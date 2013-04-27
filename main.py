#!/usr/bin/env python
#
# Copyright (c) 2013 Waleed Kadous. 

from collections import Counter
from google.appengine.ext import db
import datetime
import jinja2
import lxml
import lxml.html
import numpy
import os
import random
import string
import webapp2
import zlib


class SavedResult(db.Model):
    generated_at = db.DateTimeProperty()
    last_read = db.DateTimeProperty()
    visit_count = db.IntegerProperty()
    generated_html = db.BlobProperty()


class Answer(object):
    def __init__(self, topic, question, link, votes):
        self.topic = topic
        self.question = question
        self.link = link
        self.votes = votes

def clean_vote(x): 
    result = x.find_class('voter_count')
    if len(result) > 0: 
        return int(result[0].text_content())
    result = x.find_class('numbers')
    if len(result) > 0: 
        return int(result[0].text_content())
    return 0

def topic_question(str):
    parts = str.split(':')
    if len(parts) == 1: 
        return ('Unknown',str)
    else:
        return (parts[0], ':'.join(parts[1:]))

def answer_sort_key(answer):
    return (answer.topic,-answer.votes)

def generate_graph_data(answers):
    parts = []
    parts.append('[')
    counts = Counter([a.topic for a in answers])
    for topic, count in counts.most_common(7):
        parts.append('["%s",%d],' % (topic.encode('ascii','ignore').replace('\n',''), count))
    other_count = sum(counts.values()) - sum([count for (topic, count) in counts.most_common(7)])
    parts.append('["Other",%d]' % other_count)
    parts.append(']')
    return ''.join(parts)

def generate_vote_stats(answers):
    votes = [a.votes for a in answers]
    retval = {}
    retval['sum'] = sum(votes)
    retval['count'] = len(votes)
    retval['median'] = numpy.median(votes)
    retval['mean'] = numpy.mean(votes)
    retval['max'] = max(votes)
    return retval


def generate_key():
    # Generates a random 8 digit base 36 value. 
    return ''.join(random.choice(string.ascii_letters + string.digits) for x in range(8))

def generate_list(answers, save_key):
    root = lxml.html.fromstring(answers)
    user_name = [x for x in root.findall('.//link') if 'application/rss+xml' in x.values()][0].attrib['href'].split('/')[3]
    my_questions = root.find_class('pagedlist_item')
    questions = [(x.find_class('question_link')[0].text_content(), 
      x.find_class('question_link')[0].attrib['href'] + '/answer/' + user_name + '?share=1', 
      clean_vote(x)) for x in my_questions]
    cat_questions = [Answer(topic_question(q)[0], topic_question(q)[1],l,v) for (q,l,v) in questions]
    cat_q_s = sorted(cat_questions, key = answer_sort_key)
    template = jinja_environment.get_template('templates/result.html')
    return template.render({'answers' : cat_q_s, 
                            'user_name' : user_name,
                            'graph_data' : generate_graph_data(cat_q_s),
                            'vote_stats' : generate_vote_stats(cat_q_s),
                            'save_key' : save_key
                            })

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

class MainPage(webapp2.RequestHandler):
    def get(self):
        template = jinja_environment.get_template('templates/upload.html')
        self.response.out.write(template.render({}))
        #self.response.out.write(generate_list(os.path.join(os.path.dirname(__file__),'agnes_answers.html')))
        
class Analyze(webapp2.RequestHandler):
    def post(self):
        answers = self.request.get("answers")
        save_key = generate_key()
        html_output = generate_list(answers, save_key)
        record = SavedResult(key_name = save_key, 
                             generated_html = zlib.compress(html_output.encode('utf-8')),
                             generated_at = datetime.datetime.now(),
                             visit_count = 0)
        record.put()
        self.response.out.write(html_output)
        
class Retrieve(webapp2.RequestHandler):
    def get(self):
        key_name = self.request.path.replace('/retrieve/','')
        record = SavedResult.get_by_key_name(key_name)
        record.visit_count = record.visit_count + 1
        record.last_read = datetime.datetime.now()
        record.put()
        self.response.out.write(zlib.decompress(record.generated_html).decode('utf-8'))

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/analyze', Analyze), 
                               ('/retrieve/.*', Retrieve)],
                              debug=True)