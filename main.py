#!/usr/bin/env python
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#

import cgi
import gc
import itertools
import jinja2
import operator
import os
import webapp2
import lxml
import lxml.html
from collections import Counter


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
    else:
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
        parts.append('["%s",%d],' % (str(topic).replace('\n',''), count))
    other_count = sum(counts.values()) - sum([count for (topic, count) in counts.most_common(7)])
    parts.append('["Other",%d]' % other_count)
    parts.append(']')
    return ''.join(parts)


def generate_list(answers):
    root = lxml.html.fromstring(answers)
    user_name = [x for x in root.findall('.//link') if 'application/rss+xml' in x.values()][0].attrib['href'].split('/')[3]
    my_questions = root.find_class('pagedlist_item')
    questions = [(x.find_class('question_link')[0].text_content(), 
      x.find_class('question_link')[0].attrib['href'] + '/answer/' + user_name, 
      clean_vote(x)) for x in my_questions]
    cat_questions = [Answer(topic_question(q)[0], topic_question(q)[1],l,v) for (q,l,v) in questions]
    cat_q_s = sorted(cat_questions, key = answer_sort_key)
    template = jinja_environment.get_template('templates/result.html')
    return template.render({'answers' : cat_q_s, 
                            'user_name' : user_name,
                            'graph_data' : generate_graph_data(cat_q_s)
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
        data = self.request.get("answers")
        html_output = generate_list(data)
        self.response.out.write(html_output)

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/analyze',Analyze)], 
                              debug=True)