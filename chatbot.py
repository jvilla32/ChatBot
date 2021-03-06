#!/usr/bin/env python
# -*- coding: utf-8 -*-

# PA6, CS124, Stanford, Winter 2016
# v.1.0.2
# Original Python code by Ignacio Cases (@cases)
# Ported to Java by Raghav Gupta (@rgupta93) and Jennifer Lu (@jenylu)
# Assignment by Julian Vilalpando, Regina Nguyen, Thomas Liu
######################################################################
import csv
import math
import re
import sys
import random
import linecache
import string
import math
import pdb

import numpy as np

from movielens import ratings
from random import randint

class Chatbot:
    """Simple class to implement the chatbot for PA 6."""

    #############################################################################
    # `moviebot` is the default chatbot. Change it to your chatbot's name       #
    #############################################################################
    def __init__(self, is_turbo=False):
      self.name = 'moviebot'
      self.is_turbo = is_turbo
      self.Stemmer = PorterStemmer()
      self.recommendations = []
      self.posPoints = 0
      self.negPoints = 0
      self.prevResponse = None
      self.responseContext = None
      self.potentialTitles = None
      self.recNum = 1
      self.antiRecMode = False
      self.antiRecNum = 0
      self.recommendMode = False
      self.read_data()
      self.userName = None
      self.arbitraryInputCount = 0
      self.triviaIndexTracker = 1

    def greeting(self):
      greeting_message = "Hi! I'm MovieBot! I'm going to recommend a movie to you. Tell me about a movie that you have seen."
      return greeting_message

    def goodbye(self):
      goodbye_message = 'Have a nice day!'
      return goodbye_message


    #############################################################################
    # 2. Modules 2 and 3: extraction and transformation                         #
    #############################################################################

    def resetContext(self):
      self.responseContext = None
      self.potentialTitles = None
      self.prevResponse = None

    def validateNumTitles(self, movie_titles):
      """Checks that there is only one title mentioned"""
      if len(movie_titles) != 1:
        if len(movie_titles) == 0:
          return 0
        else:
          return 2
      else:
        return 1

    def removeYear(self, movie_title):
      start = movie_title.find( '(' )
      end = movie_title.find( ')' )
      if start != -1 and end != -1:
        return movie_title[0:start-1]
      return movie_title

    def formatTitle(self, modifiedTitle):
      modifiedTitle = self.removeYear(modifiedTitle)
      if "," in modifiedTitle:
        firstHalf = modifiedTitle.split(", ", 1)[0]
        secondHalf = modifiedTitle.split(", ", 1)[1]
        modifiedTitle = secondHalf + " " + firstHalf
      return modifiedTitle

    """Checks that title is in database"""
    def validateTitle(self, movie_title):
      ARTICLES = ['The', 'A', 'An']
      titlesIndices = []

      for title in range(len(self.titles)):
          databaseTitle = self.titles[title][0].lower()
          databaseTitle = re.sub('\(\d\d\d\d\)', '', databaseTitle)
          #modifiedTitle = self.formatTitle(databaseTitle)

          # If the movie begins with an article, moves it to the end 
          # The Fast and Furious -> Fast and Furious, The
          titleWords = movie_title.split(' ')
          for article in ARTICLES:
            if titleWords[0].lower() == article.lower():
              movie_title = ' '.join(titleWords[1:])
              movie_title += ', ' + article              

          movie_title = movie_title.lower().strip()
          databaseTitle = databaseTitle.strip()
          if not self.is_turbo:
            if movie_title == databaseTitle:
              return title
          else: # disambiguation of movie titles for series and year ambiguities
            matchRegex = "^%s(?:$| |:)" % movie_title
            matches = re.findall(matchRegex, databaseTitle)
            if len(matches) > 0:
              titlesIndices.append(title)
              
      if self.is_turbo:
        if len(titlesIndices) > 0:
          return titlesIndices

      return -1


    """Removes words in title and quotes"""
    def formatInput(self, input):
      words = re.sub('"([^"]*)"', '', input)
      words = re.sub('[.,!]', '', words)
      return words.split()
            
    def processDisambiguation(self, input):
      """Processes the response in context that it is disambiguating a previous 
      response. Looks for clarifying year or title."""
      movie_title = None
      movieIndex = None
      year = re.findall('^\d\d\d\d$', input)
      if len(year) == 1:  # Using year for clarification
        yearFormat = "(%s)" % year[0]
        for index in self.potentialTitles:
          movie = self.titles[index][0]
          if yearFormat in movie:
            movie_title = re.sub('\(\d\d\d\d\)', '', movie)
            movieIndex = index
            break
      else: # Using part of movie title for clarification
        foundIndex = []
        for index in self.potentialTitles:
          movie = self.titles[index][0]
          if input in movie:
            foundIndex.append(index)
        if len(foundIndex) != 1:
          return (-1, "Please return a valid distinguishing choice.")
        else:
          movieIndex = foundIndex[0]
          movie_title = re.sub('\(\d\d\d\d\)', '', self.titles[movieIndex][0])
      
      if movie_title == None:
        return (-1, "Please return a valid choice or year.")
      else:
        input = re.sub('"([^"]*)"', '"'+movie_title.strip()+'"', self.prevResponse)
        self.resetContext()
      
      return (1, movie_title, movieIndex, input)

    def processSentiment(self, input):
      """Identifies and responds to emotions, if any."""
      emotionKeywords = { "anger": set(["angry", "furious", "infuriate", "mad", "outrage", "rage", "upset"]), 
                          "happy": set(["happy", "joyful", "joy", "enjoy", "content", "delight", "delightful", "ecstatic", "glad", "gladden", "dazzle"]),
                          "sad": set(["sad", "depress", "depression", "unhappy", "disappoint", "disappointment"])
                        }
      emotion = None
      negated = False
      words = input.split()

      for i, word in enumerate(words):
        #word = self.Stemmer.stem(word.lower())
        oneBack = i - 1
        twoBack = i - 2
        if (oneBack >= 0 and oneBack < len(words)):
          if any(neg in words[oneBack] for neg in ["not", "n't", "no", "never"]):
            negated = True
        elif (twoBack >= 0 and twoBack < len(words)):
          if any(neg in words[twoBack] for neg in ["not", "n't", "no", "never"]):
            negated = True

        for emotionType, keywords in emotionKeywords.iteritems():
          if word.lower() in keywords or self.Stemmer.stem(word.lower()) in keywords:
            emotion = emotionType

      if (emotion == "anger" and not negated): # angry
        return "I'm sorry to hear that. Maybe you can tell me what movies you like/dislike so I can suggest a good movie to help calm you down."
      elif (emotion == "happy" and not negated) or ((emotion == "anger" or emotion == "sad") and negated): # happy
        return "I'm happy to hear that!"
      elif (emotion == "sad" and not negated) or (emotion == "happy" and negated): # sad
        return "I'm sorry to hear that. Maybe you can tell me what movies you like/dislike so I can suggest a good movie to cheer you up."

      return False

    def detectGreeting(self, input):
      """Responds to arbitrary inputs appropriately"""
      neutralGreetings = [ "hello", "hi", "bonjour", "hey"]
      enthusiasticGreetings = [ "yo ", "sup", "gday", "howdy"]
      timeGreetings = ["morning", "afternoon", "evening", "good morning", "good afternoon", "good evening"]

      inputLine = input.lower()
      inputLine = inputLine.translate(None, string.punctuation)
      inputSplit = inputLine.split()
      #if self.responseContext == None:
      #  print "responseContext: None"
      #else:
      #  print "responseContext: " + self.responseContext
      for greeting in neutralGreetings:
        if (greeting in inputSplit) and self.responseContext == None and self.userName == None:
          self.responseContext = "arbitrary"
          return "Hello there! It's great to meet you (: If you'd like, I'm always here to recommend movies!"
        elif (greeting in inputSplit) and self.responseContext == "arbitrary" and self.userName == None:
          self.responseContext = "name"
          #print "new responseContext: " + self.responseContext
          return "Hey again! It seems you're not interested in a movie recommendation. What's your name then?"
        elif (greeting in inputLine or greeting in inputSplit) and self.userName != None:
          return "Hey there again, " + self.userName + "!"
      
      for greeting in enthusiasticGreetings:
        if (greeting in inputSplit) and self.responseContext == None and self.userName == None:
          self.responseContext = "arbitrary"
          return "Howdy! It's a pleasure to meet you (:"
        elif (greeting in inputSplit) and self.responseContext == "arbitrary" and self.userName == None:
          self.responseContext = "name"
          return "Howdy again! It seems you're not interested in a movie recommendation. What's your name then?"
        elif (greeting in inputSplit) and self.userName != None:
          return "Howdy howdy, " + self.userName + "!"

      for greeting in timeGreetings:
        if "morning" in greeting and greeting in inputLine and self.responseContext == None and self.userName == None:
          self.responseContext = "arbitrary"
          return "It's a great morning! Good morning to you too (:"
        elif "morning" in greeting and greeting in inputLine  and self.responseContext == "arbitrary" and self.userName == None:
          self.responseContext = "name"
          return "Good morning! It seems you're not interested in a movie recommendation. What's your name then?"
        elif "morning" in greeting and greeting in inputLine  and self.userName != None:
          return "Good morning again, " + self.userName + "!"

        elif "afternoon" in greeting and greeting in inputLine and self.responseContext == None and self.userName == None:
          self.responseContext = "arbitrary"
          return "It's a beautiful afternoon! Good afternoon to you too (:"
        elif "afternoon" in greeting and greeting in inputLine  and self.responseContext == "arbitrary" and self.userName == None:
          self.responseContext = "name"
          return "Good afternoon! It seems you're not interested in a movie recommendation. What's your name then?"
        elif "afternoon" in greeting and greeting in inputLine  and self.userName != None:
          return "Good afternoon again, " + self.userName + "!"

        elif "evening" in greeting and greeting in inputLine and self.responseContext == None and self.userName == None:
          self.responseContext = "arbitrary"
          return "It's a wonderful evening! Good evening to you too (:"
        elif "evening" in greeting and greeting in inputLine  and self.responseContext == "arbitrary" and self.userName == None:
          self.responseContext = "name"
          return "Good evening! It seems you're not interested in a movie recommendation. What's your name then?"
        elif "evening" in greeting and greeting in inputLine  and self.userName != None:
          return "Good evening again, " + self.userName + "!"

      self.resetContext()
      return False # not a greeting

    def checkName(self, input):
      #print "CHECKING NAME!!!"
      nameInputRegexes = [r'my\sname\sis\s(\w+)',
        r'im\s(\w+)',
        r'i\sam\s(\w+)',
        r'my\snames\s(\w+)',
        r'call\sme\s(\w+)',
        r'you\scan\scall\sme\s(\w+)',
        r'i\sgo\sby\s(\w+)']
      nameInput = input.lower()
      nameInput = nameInput.translate(None, string.punctuation)
      for regex in nameInputRegexes:
        pattern = re.compile(regex, re.IGNORECASE)
        result = pattern.search(nameInput)
        if result != None:
          #print "FOUND SOMETHING!"
          nameList = open('data/first_names.txt').read()
          potentialName = result.group(1).title()
          if potentialName.upper() in nameList:
            if self.userName == None:
              self.userName = potentialName.capitalize()
              self.resetContext()
              return "Well, it's certainly nice to meet you, " + self.userName + "! Now tell me something, or alternatively tell me about a movie you've seen."
            elif self.userName != None and self.userName != potentialName:
              self.userName = potentialName.capitalize()
              self.resetContext()
              return "Oh, is that what you'd prefer me to call you? Well, hello there " + self.userName + "."
            elif self.userName != None and self.userName == potentialName:
              return "You've already told me that's your name! I don't forget (: Hi again, " + self.userName + "."
      return False

    def processName(self, input):
      nameInputRegexes = [r'my\sname\sis\s(\w+)',
        r'im\s(\w+)',
        r'i\sam\s(\w+)',
        r'its\s(\w+)',
        r'it\sis\s(\w+)',
        r'my\snames\s(\w+)',
        r'call\sme\s(\w+)',
        r'you\scan\scall\sme\s(\w+)',
        r'i\sgo\sby\s(\w+)']
      nameInput = input.lower()
      nameInput = nameInput.translate(None, string.punctuation)
      detectedName = False
      for regex in nameInputRegexes:
        pattern = re.compile(regex, re.IGNORECASE)
        result = pattern.match(nameInput)
        if result != None:
          detectedName = True
          self.userName = result.group(1).title()
          self.resetContext()
          return "Well, it's certainly nice to meet you, " + self.userName + "! Now tell me something, or alternatively tell me about a movie you've seen."
      nameInput = nameInput.split()
      potentialName = nameInput[0]
      nameList = open('data/first_names.txt').read()
      if potentialName.upper() in nameList:
        detectedName = True
        self.resetContext()
        self.userName = potentialName.title()
        return "Well, it's certainly nice to meet you, " + self.userName + "! Now tell me something, or alternatively tell me about a movie you've seen."
      if detectedName == False:
        self.resetContext()
        return "Sorry, I didn't quite catch your name. Anyways, we can go back to talking about movies!"
      return False

    def detectQuestion(self, input):
      questionWords = ["what", "who", "when", "where", "why", "how"]
      if "?" in input:
        return True
      userInput = input.lower().split()
      for word in questionWords:
        if word in userInput:
          return True
      if "can you" in input.lower() or "could you" in input.lower() or "will you" in input.lower() or "would you" in input.lower() or "did you" in input.lower():
        return True
      return False

    def replaceWord(self, oldWord, newWord, string):
      tokenized = string.split()
      for index, token in enumerate(tokenized):
        if token == oldWord:
          tokenized[index] = newWord
      newString = " ".join(str(word) for word in tokenized)
      return newString

    def processStructuredQuestion(self, input):
      if self.detectQuestion(input) == False:
        return False

      structuredQuestionRegexes = {r'\s?what\sis\s([\w|\s]*)[\n|\.|\?|,]' : "is",
        r'\s?can\syou\s([\w|\s]*)[\n|\.|\?|,]' : "can",
        r'\s?would\syou\s([\w|\s]*)[\n|\.|\?|,]' : "would",
        r'\s?what\sare\s([\w|\s]*)[\n|\.|\?|,]' : "are",
        r'\s?could\syou\s([\w|\s]*)[\n|\.|\?|,]' : "could",
        r'\s?who\sare\s([\w|\s]*)[\n|\.|\?|,]' : "are",
        r'\s?who\sis\s([\w|\s]*)[\n|\.|\?|,]' : "is",
        r'\s?where\sis\s([\w|\s]*)[\n|\.|\?|,]' : "is",
        r'\s?what\sare\s([\w|\s]*)[\n|\.|\?|,]' : "are",
        r'\s?when\sis\s([\w|\s]*)[\n|\.|\?|,]' : "is",
        r'\s?when\sare\s([\w|\s]*)[\n|\.|\?|,]' : "are",
        r'\s?why\sis\s([\w|\s]*)[\n|\.|\?|,]' : "is",
        r'\s?will\syou\s([\w|\s]*)[\n|\.|\?|,]' : "will",
        r'\s?would\syou\s([\w|\s]*)[\n|\.|\?|,]' : "would",
        r'\s?did\syou\s([\w|\s]*)[\n|\.|\?|,]' : "did",
        r'\s?why\sare\s([\w|\s]*)[\n|\.|\?|,]' : "are"}
      inputQuestion = input.lower()
      inputQuestion = " " + inputQuestion + "\n"

      for regex, keyWord in structuredQuestionRegexes.iteritems():
        pattern = re.compile(regex, re.IGNORECASE)
        result = pattern.match(inputQuestion)
        if result != None and self.userName == None:
          phrase = result.group(1)

          if "me" in phrase.split() and "you" not in phrase.split():
            phrase = self.replaceWord("me", "you", phrase)
          elif "you" in phrase.split() and "me" not in phrase.split():
            phrase = self.replaceWord("you", "me", phrase)
          elif "you" in phrase.split() and "me" in phrase.split(): # both in phrase so switch positions
            phrase = self.replaceWord("you", "xxxx", phrase) # xxxx = filler word to perform this switching
            phrase = self.replaceWord("me", "you", phrase)
            phrase = self.replaceWord("xxxx", "I", phrase)
          if "my" in phrase.split() and "your" not in phrase.split():
            phrase = self.replaceWord("my", "your", phrase)
          elif "your" in phrase.split() and "my" not in phrase.split():
            phrase = self.replaceWord("your", "my", phrase)
          if "mine" in phrase.split() and "yours" not in phrase.split():
            phrase = self.replaceWord("mine", "yours", phrase)
          elif "yours" in phrase.split() and "mine" not in phrase.split():
            phrase = self.replaceWord("yours", "mine", phrase)

          phrase = phrase.strip()
          if keyWord == "is":
            return phrase.capitalize() + " isn't something I'm familiar with, sorry."
          elif keyWord == "are":
            return phrase.capitalize() + " aren't within my area of expertise, sorry about that. I'd love to talk about something else with you though!"
          elif keyWord == "could":
            return "To be honest, I could "+ phrase + ", but I'd just rather talk about something else."
          elif keyWord == "would":
            return "No, I wouldn't "+ phrase + " even if I could!"
          elif keyWord == "can":
            return "Sorry, I can't really "+ phrase + "."
          elif keyWord == "will":
            return "Sorry, unfortunately, I will not "+ phrase + "."
          elif keyWord == "would":
            return "No, I don't think I would "+ phrase + "."
          elif keyWord == "did":
            return "Nope, I almost swear I didn't "+ phrase + "."
        
        if result != None and self.userName != None:
          phrase = result.group(1)

          if "me" in phrase.split() and "you" not in phrase.split():
            phrase = self.replaceWord("me", "you", phrase)
          elif "you" in phrase.split() and "me" not in phrase.split():
            phrase = self.replaceWord("you", "me", phrase)
          if "my" in phrase.split() and "your" not in phrase.split():
            phrase = self.replaceWord("my", "your", phrase)
          elif "your" in phrase.split() and "my" not in phrase.split():
            phrase = self.replaceWord("your", "my", phrase)
          if "mine" in phrase.split() and "yours" not in phrase.split():
            phrase = self.replaceWord("mine", "yours", phrase)
          elif "yours" in phrase.split() and "mine" not in phrase.split():
            phrase = self.replaceWord("yours", "mine", phrase)

          phrase = phrase.strip()
          if keyWord == "is":
            return phrase.capitalize() + " isn't something I'm qualified to speak about, sorry " + self.userName + "."
          elif keyWord == "are":
            return phrase.capitalize() + " aren't within my area of expertise. Sorry about that, " + self.userName + ". I'd love to talk about something else with you though!"
          elif keyWord == "could":
            return "To be honest, " + self.userName + ", I could "+ phrase + ", but I'd just rather talk about something else."
          elif keyWord == "would":
            return "No, " + self.userName + ", I wouldn't "+ phrase + " even if I could!"
          elif keyWord == "can":
            return "Sorry, " + self.userName + ", I can't really "+ phrase + "."
          elif keyWord == "will":
            return "Sorry, " + self.userName + ", unfortunately I will not "+ phrase + "."
          elif keyWord == "would":
            return "No, " + self.userName + ", I don't think I would "+ phrase + "."
          elif keyWord == "did":
            return "Nope, " + self.userName + ", I almost swear I didn't "+ phrase + "."
             
      return False

    def checkForPotentialMovie(self, input):
      quotationsCount = input.count('"')
      if quotationsCount == 1 and self.userName != None:
        return "Hmm, " + self.userName + ", were you trying to tell me about a movie? If so, just remember to put double quotes on each end of the movie title!"
      elif quotationsCount == 1 and self.userName == None:
        return "Hmm, were you trying to tell me about a movie? If so, just remember to put double quotes on each end of the movie title!"
      return False

    def processArbitraryInput(self, input):
      """Responds to arbitrary inputs appropriately"""
      #print "PROCESSING ARBITRARY INPUT!!"
      quickCheck = self.checkForPotentialMovie(input)
      if quickCheck != False:
        return quickCheck
      detectName = self.checkName(input)
      if detectName != False:
        return detectName
      if self.responseContext == "name":
        response = self.processName(input)
        if response != False:
          return response
      if self.detectQuestion(input) == False:
        greeting = self.detectGreeting(input)
        if greeting != False: #user gave a greeting
          return greeting
      structuredResponse = self.processStructuredQuestion(input)
      if structuredResponse != False:
        return structuredResponse

      # for the case of everything else arbitrary..
      catchAllResponses = [ "Hm, that's not really what I want to talk about right now, let's go back to movies!",
                            "Ok, got it.",
                            "I was thinking the same thing.",
                            "Umm, okay.",
                            "Oh, I was about to say the same thing to you.",
                            "Oh cool, tell me more!",
                            "I've heard that before.",
                            "Is that so?",
                            "Oh, right. Of course.",
                            "Well if you say so...",
                            "I see, well I'll keep that in mind.",
                            "Mhmm. And?",
                            "Interesting... can you tell me more about that?"]
      
      questionResponses = [ "I'm not sure if I'm qualified to answer that question right now, I'm sorry.",
                            "To be honest, I'm not entirely sure...",
                            "It's hard to say.",
                            "I may not be able to answer that, but I'm quite the expert on movies!",
                            "That's a great question, but I'm probably not the right person to ask",
                            "I can see why you'd want to know, but I just can't answer that.",
                            "You've stumped me - I've got no clue!",
                            "I don't actually know much about that - I'm more of an expert on movies.",
                            "Hmm, I need to think about it.",
                            "I'll get back to you about that one, but in the meantime we can talk about movies!" ]

      userInput = input.lower().split()
      if self.detectQuestion(input):
        return random.choice(questionResponses)
      else:
        return random.choice(catchAllResponses)
      return False

    def calculateEditDistance(self, misspelled, title):
      """Uses Levenshtein algorithm on slide 14 of Edit Distance slides 
      to calculate minimum edit distance between titles."""
      height = len(misspelled) 
      width = len(title)
      distances = [[0 for i in range(width+1)] for j in range(height+1)]

      # Initialization
      for i in range(0, height+1):
        distances[i][0] = i
      for j in range(0, width+1):
        distances[0][j] = j

      # Recurrence relation
      for i in range(1, height+1):
        for j in range(1, width+1):
          d = [distances[i-1][j] + 1, distances[i][j-1] + 1]
          if i-1 > height or j-1 > width or misspelled[i-1] != title[j-1]:
            d.append(distances[i-1][j-1] + 2)
          else:
            d.append(distances[i-1][j-1])
          distances[i][j] = min(d)

      return distances[height][width]

    def spellCheckTitle(self, misspelled):
      """Finds the movie title index with the minimum edit distance from 
      the given title."""
      minDistance = float('inf')
      possTitleIndex = -1
      for i in range(0, len(self.titles)):
        title = self.titles[i][0]
        title = re.sub('\(\d\d\d\d\)', '', title).strip()
        if abs(len(misspelled) - len(title)) <= minDistance:
          editDistance = self.calculateEditDistance(misspelled, title)
          if editDistance < minDistance:
            minDistance = editDistance
            possTitleIndex = i
      if minDistance < 3*len(misspelled.split()):   # If < about 3 errors per word in the title
        return possTitleIndex
      else:
        return -1

    def checkYesNoResponse(self, input):
      inputLine = input.lower().split()
      if "yes" in inputLine or "Y" in inputLine or "yeah" in inputLine or "yup" in inputLine or "ya" in inputLine or "yea" in inputLine:
        if ("no" not in inputLine and "nope" not in inputLine and "nah" not in inputLine and "never" not in inputLine and "not" not in inputLine):
          return True
      else:
        return False 

    def process(self, input):
      """Takes the input string from the REPL and call delegated functions
      that
        1) extract the relevant information and
        2) transform the information into a response to the user
      """
      #############################################################################
      # TODO: Implement the extraction and transformation in this method, possibly#
      # calling other functions. Although modular code is not graded, it is       #
      # highly recommended                                                        #
      #############################################################################
      movie_title = None
      movieIndex = None

      if(self.antiRecMode):
        if (input == "Y"):
          self.allRatings = sorted(self.allRatings, key=lambda x: x[1])
          topFive = self.allRatings[:5]
          response = "I'd recommend staying away from:\n"
          for pair in topFive:
            response += str(self.titles[pair[0]]) + "\n"
          response += "Nice chatting. Have a good one (Please type :quit)"
          return response
        else:
          return "Nice chatting. Have a good one (Please type :quit)"

      if(self.recommendMode):
        if(input == "Y"):
          self.recNum += 1
          recommendation = self.recommend()
          return "I suggest you watch \"" + recommendation + "\". Would you like to hear another recommendation? [Y/N]"
        else:
          self.antiRecMode = True
          return "Okay. Before you go, would you like to know which movies you should avoid? [Y/N]"

      if self.is_turbo and self.responseContext != None:  # special responses with context
        if self.responseContext == "disambiguation":
          response = self.processDisambiguation(input)
          if response[0] == -1:
            return response[1]
          else:
            movie_title = response[1].strip()
            movieIndex = response[2]
            input = response[3]
        elif self.responseContext == "spellCheck":
          if input == "Y":  # If ChatBot suggested correct movie title spelling
            movieIndex = self.potentialTitles
            movie_title = self.titles[movieIndex][0]
            input = re.sub('"([^"]*)"', '"'+movie_title.strip()+'"', self.prevResponse)
            self.resetContext()
          elif input == "N":
            self.resetContext()
            return "My mistake! Can you repeat your original statement, making sure the movie title is valid?"
          else:
            return "Please respond Y or N."
        elif self.responseContext == "arbitrary" or self.responseContext == "name":
          response = self.processArbitraryInput(input)
          if response != False:
            return response

      else: # treat response as normal
        movie_titles = re.findall('"([^"]*)"', input)
        numTitles = self.validateNumTitles(movie_titles)
        if (numTitles != 1):
          if numTitles >= 2:
            if self.userName == None:
              return "Hm, that sounds great, but could you tell me about them one movie at a time? Go ahead!"
            else:
              return "Hm, " + self.userName + ", that sounds great, but could you tell me about them one movie at a time? Go ahead!"
          else: 
            foundSentiment = self.processSentiment(input)
            if foundSentiment:
              return foundSentiment
            elif self.is_turbo: # did not find sentiment, input is something else
              return self.processArbitraryInput(input)
            else:
              return self.checkForPotentialMovie(input)

        movie_title = movie_titles[0]
        movieIndex = self.validateTitle(movie_title)

        for pair in self.recommendations:
          if pair[0] == movieIndex:
            return "You have already given a review on " + self.titles[movieIndex][0]

        if(movieIndex == -1):
          # Tries to spell check to see if there's a similar enough title
          if self.is_turbo:
            possTitleIndex = self.spellCheckTitle(movie_titles[0])
            if possTitleIndex == -1:
              return "I'm not familiar with the movie \"" + movie_title + "\". Could you try another movie?"
            else:
              possTitle = self.titles[possTitleIndex][0]
              self.prevResponse = input
              self.responseContext = "spellCheck"
              self.potentialTitles = possTitleIndex
              return "Did you mean \"" + possTitle + "\" [Y/N]?"
          else:
            return "I'm not familiar with the movie \"" + movie_title + "\". Could you try another movie?"
        elif self.is_turbo: # disambiguation of movie titles for series and year ambiguities
          if len(movieIndex) == 1:
            movie_title = self.titles[movieIndex[0]][0]
            movie_title = self.formatTitle(movie_title)
            movieIndex = movieIndex[0]
          else:
            choices = ""
            for i in range(0, len(movieIndex)-1):
              choices += str(self.titles[movieIndex[i]][0]).strip() + ", " # TODO: fix extra space before comma
            choices += "or " + str(self.titles[movieIndex[len(movieIndex)-1]][0])
            self.prevResponse = input
            self.responseContext = "disambiguation"
            self.potentialTitles = movieIndex
            return "Did you mean " + choices + " (please provide a distinguishing phrase or the year)?" 
        else:
          movie_title = self.titles[movieIndex][0]
          movie_title = self.formatTitle(movie_title)

      positivity = 0
      negativity = 0
      dataPoints = 0


      words = self.formatInput(input)
      for i, word in enumerate(words):
        word = self.Stemmer.stem(word.lower())

        if (word in self.sentiment):
          sentiment = self.sentiment[word]

          booster2 = False
          booster = False
          if (word in ["love", "hate", "favorite"]):
            booster = True

          negated = False
          oneBack = i - 1
          twoBack = i - 2
          oneForward = i + 1
          twoForward = i + 2
          if (oneForward >= 0 and oneForward < len(words)):
            if (words[oneForward].lower() in ["really", "very"]):
              booster2 = True
          if (twoForward >= 0 and twoForward < len(words)):
            if (words[twoForward].lower() in ["really", "very"]):
              booster2 = True

          if (oneBack >= 0 and oneBack < len(words)):
            if any(neg in words[oneBack] for neg in ["not", "n't", "no"]):
              negated = True
            if (words[oneBack].lower() in ["really", "very"]):
              booster2 = True
          elif (twoBack >= 0 and twoBack < len(words)):
            if any(neg in words[twoBack] for neg in ["not", "n't", "no"]):
              negated = True
            if (words[twoBack].lower() in ["really", "very"]):
              booster2 = True

          if (negated):
            if (sentiment == "pos"):
              sentiment = "neg"
            elif (sentiment == "neg"):
              sentiment = "pos"

          boostScore = 1
          if (booster and self.is_turbo):
            boostScore += 1
          if (booster2 and self.is_turbo):
            boostScore += 1

          if (sentiment == "pos"):
            positivity += 1*boostScore
          elif (sentiment == "neg"):
            negativity += 1*boostScore

      titleRating = 0
      if (positivity > negativity):
        self.posPoints += 1
        titleRating = 1
        response = "You liked \"" + movie_title + "\". Thank you. "
      elif(negativity > positivity):
        self.negPoints += 1
        titleRating = -1
        response = "You disliked \"" + movie_title + "\". Thank you. "
      elif(positivity == 0 and negativity == 0):
        response = "How did you feel about " + movie_title + "? (Please mention " + movie_title + " in your response)"
        return response
      elif(positivity == negativity):
        response = "I couldn't decipher your sentiment towards " + movie_title + ". Please try again."
        return response

      ratingTuple = (movieIndex, titleRating)
      self.recommendations.append(ratingTuple)

      if (len(self.recommendations) >= 5):
        if (self.posPoints == 0):
          response += "I need at least one positive review before making my assessment"
        elif(self.negPoints == 0):
          response += "I need at least one negative review before making my assessment"
        else:
          print(response)
          print("Processing recommendation...")
          recommendation = self.recommend()
          self.recommendMode = True
          response = "That's enough for me to make a recommendation. I suggest you watch \"" + recommendation + "\". Would you like to hear another recommendation? [Y/N]"
      else:
        response += "Tell me about another movie you have seen"

      return response


    #############################################################################
    # 3. Movie Recommendation helper functions                                  #
    #############################################################################

    def read_data(self):
      """Reads the ratings matrix from file"""
      # This matrix has the following shape: num_movies x num_users
      # The values stored in each row i and column j is the rating for
      # movie i by user j
      self.titles, self.ratings = ratings()
      reader = csv.reader(open('data/sentiment.txt', 'rb'))
      self.sentiment = dict(reader)
      for key in self.sentiment.keys():
        newKey = self.Stemmer.stem(key.lower())
        self.sentiment[newKey] = self.sentiment.pop(key)

    def binarize(self):
      """Modifies the ratings matrix to make all of the ratings binary"""

      for movie in range(len(self.ratings)):
        for rating in range(len(self.ratings[movie])):
          value = self.ratings[movie][rating]
          if (value >= 3):
            self.ratings[movie][rating] = 1
          elif(value == 0):
            self.ratings[movie][rating] = 0
          elif(value <= 2.5):
            self.ratings[movie][rating] = -1

    def distance(self, title1, title2):
      """Calculates a given distance function between rating vectors of two titles"""
      vector1 = self.ratings[title1]
      vector2 = self.ratings[title2]

      magnitude1 = 0
      magnitude2 = 0

      for rating in vector1:
        magnitude1 += math.pow(rating,2)
      for rating in vector2:
        magnitude2 += math.pow(rating,2)

      if (magnitude1 == 0 or magnitude2 == 0):
        return 0

      magnitude1 = math.sqrt(magnitude1)
      magnitude2 = math.sqrt(magnitude2)

      numerator = 0
      for index in range(len(vector2)):
        numerator += vector2[index] * vector1[index]

      return numerator/(magnitude2*magnitude1)

    def recommend(self):
      """Generates a list of movies based on the input vector u using
      collaborative filtering"""
      # TODO: Implement a recommendation function that takes a user vector u
      # and outputs a list of movies recommended by the chatbot

      # self.recommendations = [(5624, 1), (6272, 1), (6562, 1), (6809, 1), (1580, -1)] #like saw 

      takenTitles = []
      for pair in self.recommendations:
        takenTitles.append(pair[0])

      if(self.recommendMode):
        recNum = self.recNum
        for rating in self.allRatings:
          movieIndex = rating[0]
          if movieIndex not in takenTitles:
            recNum -= 1
            if (recNum == 0):
              return self.titles[movieIndex][0]

      self.allRatings = []
      
      
      self.binarize()


      for movie in range(len(self.ratings)):
        numerator = 0
        for pair in self.recommendations:
          title = pair[0]
          rating = pair[1]
          similarity = self.distance(movie, title)
          numerator += similarity * rating
        rating = numerator
        self.allRatings.append((movie, rating))


      self.allRatings = sorted(self.allRatings, key=lambda x: x[1], reverse=True)
      recNum = self.recNum
      for rating in self.allRatings:
        movieIndex = rating[0]
        if movieIndex not in takenTitles:
          recNum -= 1
          if (recNum == 0):
            return self.titles[movieIndex][0]

      return "None"




    #############################################################################
    # 4. Debug info                                                             #
    #############################################################################

    def debug(self, input):
      """Returns debug information as a string for the input string from the REPL"""
      # Pass the debug information that you may think is important for your
      # evaluators
      debug_info = 'debug info'
      return debug_info


    #############################################################################
    # 5. Write a description for your chatbot here!                             #
    #############################################################################
    def intro(self):
      return """
      Hello there! Welcome to our chatbot! In our Creative / TURBO mode, we have implemented 
      features that include:
      --------------------------------------------------------------
      - Handling Fine-Grained Sentiment Extraction 
          Checks for [love, hate, favorite] and [very, really] as features when deciphering 
          sentiment (double to triple weighting for one or both features)).
      - Responding to arbitrary input
          Gives a range of plausible catch-all answers to inputs that are statements. Has strategies in place to respond
          appropriately (using what was asked and said by the user) to structured questions.
      - Spell checking
          If you incorrectly spell the basic movie title (works for "Titnic" but now "Harry Ptter" 
          which is not a standalone movie title).
      - Speaking very fluently
          Has the capacity to learn the user's name, to make it feel more like talking to a friend. If given the user's name, the bot will remember 
          the name and use it to give more persoanlized responses thereafter. The bot can also detect / distinguish between  most questions and 
          statements (will respond appropriately), and it can also detect a number of standard greetings. Furthermore, it 
          maintains conversation organically by giving neutral comments or asking further questions. 
      - Disallowing repeat titles
          Checks to see if you have already expressed your opinion on a movie.
      - Disambiguating movie titles for series and year ambiguities 
          Prompts you for a clarifying part of the movie name or year, like if you type in I like 
          "Harry Potter" it will give the list of clarifying choices)
      - Identifying and responding to emotion 
          Can detect anger, sadness, and happiness in statements without movie titles.
      - Offering multiple recommendations
          Asks if you want another recommendation after you receive your first one.
      - Offering to display least compatible recommendations
          Asks if you want to see five movies that you will probably dislike after you have received 
          your first recommendation.

      Elaborating on other features:
      - Name learning and recognition
          The user can tell the bot their name, and the bot will remember the name and use it in subseqent responses. Furthermore, the
          user can also change their name throughout the conversation, for example:
            user: Nice to meet you, my name is Thomas
            bot: Well, it's certainly nice to meet you, Thomas! Now tell me something, or alternatively tell me about a movie you've seen.
            user: Actually, you can call me Tom
            bot: Oh, is that what you'd prefer me to call you? Well, hello there Tom. 
      - Robust question answering capacities
          The bot is able to process structured questions including: what is / can you / would you / what are / who are / 
          who is / where is / when is / when are / why is / will you / did you / why are... It achieves this by also using parts of
          the input question, and is able to respond with proper grammar if give pronouns in the input. For example: 
            user: Can you give me your phone number?
            bot: Sorry, I can't really give you my number.
            user: What is the meaning of your life?
            bot: The meaning of my life isn't something I'm qualified to speak about, sorry.
            user: Where is the best restaurant in San Francisco?
            bot: The best restaurant in San Srancisco isn't something I'm qualified to speak about, sorry.

      """


    #############################################################################
    # Auxiliary methods for the chatbot.                                        #
    #                                                                           #
    # DO NOT CHANGE THE CODE BELOW!                                             #
    #                                                                           #
    #############################################################################

    def bot_name(self):
      return self.name


if __name__ == '__main__':
    Chatbot()





class PorterStemmer:
  def __init__(self):
      """The main part of the stemming algorithm starts here.
      b is a buffer holding a word to be stemmed. The letters are in b[k0],
      b[k0+1] ... ending at b[k]. In fact k0 = 0 in this demo program. k is
      readjusted downwards as the stemming progresses. Zero termination is
      not in fact used in the algorithm.

      Note that only lower case sequences are stemmed. Forcing to lower case
      should be done before stem(...) is called.
      """

      self.b = ""  # buffer for word to be stemmed
      self.k = 0
      self.k0 = 0
      self.j = 0   # j is a general offset into the string

  def cons(self, i):
      """cons(i) is TRUE <=> b[i] is a consonant."""
      if self.b[i] == 'a' or self.b[i] == 'e' or self.b[i] == 'i' or self.b[i] == 'o' or self.b[i] == 'u':
          return 0
      if self.b[i] == 'y':
          if i == self.k0:
              return 1
          else:
              return (not self.cons(i - 1))
      return 1

  def m(self):
      """m() measures the number of consonant sequences between k0 and j.
      if c is a consonant sequence and v a vowel sequence, and <..>
      indicates arbitrary presence,

         <c><v>       gives 0
         <c>vc<v>     gives 1
         <c>vcvc<v>   gives 2
         <c>vcvcvc<v> gives 3
         ....
      """
      n = 0
      i = self.k0
      while 1:
          if i > self.j:
              return n
          if not self.cons(i):
              break
          i = i + 1
      i = i + 1
      while 1:
          while 1:
              if i > self.j:
                  return n
              if self.cons(i):
                  break
              i = i + 1
          i = i + 1
          n = n + 1
          while 1:
              if i > self.j:
                  return n
              if not self.cons(i):
                  break
              i = i + 1
          i = i + 1

  def vowelinstem(self):
      """vowelinstem() is TRUE <=> k0,...j contains a vowel"""
      for i in range(self.k0, self.j + 1):
          if not self.cons(i):
              return 1
      return 0

  def doublec(self, j):
      """doublec(j) is TRUE <=> j,(j-1) contain a double consonant."""
      if j < (self.k0 + 1):
          return 0
      if (self.b[j] != self.b[j-1]):
          return 0
      return self.cons(j)

  def cvc(self, i):
      """cvc(i) is TRUE <=> i-2,i-1,i has the form consonant - vowel - consonant
      and also if the second c is not w,x or y. this is used when trying to
      restore an e at the end of a short  e.g.

         cav(e), lov(e), hop(e), crim(e), but
         snow, box, tray.
      """
      if i < (self.k0 + 2) or not self.cons(i) or self.cons(i-1) or not self.cons(i-2):
          return 0
      ch = self.b[i]
      if ch == 'w' or ch == 'x' or ch == 'y':
          return 0
      return 1

  def ends(self, s):
      """ends(s) is TRUE <=> k0,...k ends with the string s."""
      length = len(s)
      if s[length - 1] != self.b[self.k]: # tiny speed-up
          return 0
      if length > (self.k - self.k0 + 1):
          return 0
      if self.b[self.k-length+1:self.k+1] != s:
          return 0
      self.j = self.k - length
      return 1

  def setto(self, s):
      """setto(s) sets (j+1),...k to the characters in the string s, readjusting k."""
      length = len(s)
      self.b = self.b[:self.j+1] + s + self.b[self.j+length+1:]
      self.k = self.j + length

  def r(self, s):
      """r(s) is used further down."""
      if self.m() > 0:
          self.setto(s)

  def step1ab(self):
      """step1ab() gets rid of plurals and -ed or -ing. e.g.

         caresses  ->  caress
         ponies    ->  poni
         ties      ->  ti
         caress    ->  caress
         cats      ->  cat

         feed      ->  feed
         agreed    ->  agree
         disabled  ->  disable

         matting   ->  mat
         mating    ->  mate
         meeting   ->  meet
         milling   ->  mill
         messing   ->  mess

         meetings  ->  meet
      """
      if self.b[self.k] == 's':
          if self.ends("sses"):
              self.k = self.k - 2
          elif self.ends("ies"):
              self.setto("i")
          elif self.b[self.k - 1] != 's':
              self.k = self.k - 1
      if self.ends("eed"):
          if self.m() > 0:
              self.k = self.k - 1
      elif (self.ends("ed") or self.ends("ing")) and self.vowelinstem():
          self.k = self.j
          if self.ends("at"):   self.setto("ate")
          elif self.ends("bl"): self.setto("ble")
          elif self.ends("iz"): self.setto("ize")
          elif self.doublec(self.k):
              self.k = self.k - 1
              ch = self.b[self.k]
              if ch == 'l' or ch == 's' or ch == 'z':
                  self.k = self.k + 1
          elif (self.m() == 1 and self.cvc(self.k)):
              self.setto("e")

  def step1c(self):
      """step1c() turns terminal y to i when there is another vowel in the stem."""
      if (self.ends("y") and self.vowelinstem()):
          self.b = self.b[:self.k] + 'i' + self.b[self.k+1:]

  def step2(self):
      """step2() maps double suffices to single ones.
      so -ization ( = -ize plus -ation) maps to -ize etc. note that the
      string before the suffix must give m() > 0.
      """
      if self.b[self.k - 1] == 'a':
          if self.ends("ational"):   self.r("ate")
          elif self.ends("tional"):  self.r("tion")
      elif self.b[self.k - 1] == 'c':
          if self.ends("enci"):      self.r("ence")
          elif self.ends("anci"):    self.r("ance")
      elif self.b[self.k - 1] == 'e':
          if self.ends("izer"):      self.r("ize")
      elif self.b[self.k - 1] == 'l':
          if self.ends("bli"):       self.r("ble") # --DEPARTURE--
          # To match the published algorithm, replace this phrase with
          #   if self.ends("abli"):      self.r("able")
          elif self.ends("alli"):    self.r("al")
          elif self.ends("entli"):   self.r("ent")
          elif self.ends("eli"):     self.r("e")
          elif self.ends("ousli"):   self.r("ous")
      elif self.b[self.k - 1] == 'o':
          if self.ends("ization"):   self.r("ize")
          elif self.ends("ation"):   self.r("ate")
          elif self.ends("ator"):    self.r("ate")
      elif self.b[self.k - 1] == 's':
          if self.ends("alism"):     self.r("al")
          elif self.ends("iveness"): self.r("ive")
          elif self.ends("fulness"): self.r("ful")
          elif self.ends("ousness"): self.r("ous")
      elif self.b[self.k - 1] == 't':
          if self.ends("aliti"):     self.r("al")
          elif self.ends("iviti"):   self.r("ive")
          elif self.ends("biliti"):  self.r("ble")
      elif self.b[self.k - 1] == 'g': # --DEPARTURE--
          if self.ends("logi"):      self.r("log")
      # To match the published algorithm, delete this phrase

  def step3(self):
      """step3() dels with -ic-, -full, -ness etc. similar strategy to step2."""
      if self.b[self.k] == 'e':
          if self.ends("icate"):     self.r("ic")
          elif self.ends("ative"):   self.r("")
          elif self.ends("alize"):   self.r("al")
      elif self.b[self.k] == 'i':
          if self.ends("iciti"):     self.r("ic")
      elif self.b[self.k] == 'l':
          if self.ends("ical"):      self.r("ic")
          elif self.ends("ful"):     self.r("")
      elif self.b[self.k] == 's':
          if self.ends("ness"):      self.r("")

  def step4(self):
      """step4() takes off -ant, -ence etc., in context <c>vcvc<v>."""
      if self.b[self.k - 1] == 'a':
          if self.ends("al"): pass
          else: return
      elif self.b[self.k - 1] == 'c':
          if self.ends("ance"): pass
          elif self.ends("ence"): pass
          else: return
      elif self.b[self.k - 1] == 'e':
          if self.ends("er"): pass
          else: return
      elif self.b[self.k - 1] == 'i':
          if self.ends("ic"): pass
          else: return
      elif self.b[self.k - 1] == 'l':
          if self.ends("able"): pass
          elif self.ends("ible"): pass
          else: return
      elif self.b[self.k - 1] == 'n':
          if self.ends("ant"): pass
          elif self.ends("ement"): pass
          elif self.ends("ment"): pass
          elif self.ends("ent"): pass
          else: return
      elif self.b[self.k - 1] == 'o':
          if self.ends("ion") and (self.b[self.j] == 's' or self.b[self.j] == 't'): pass
          elif self.ends("ou"): pass
          # takes care of -ous
          else: return
      elif self.b[self.k - 1] == 's':
          if self.ends("ism"): pass
          else: return
      elif self.b[self.k - 1] == 't':
          if self.ends("ate"): pass
          elif self.ends("iti"): pass
          else: return
      elif self.b[self.k - 1] == 'u':
          if self.ends("ous"): pass
          else: return
      elif self.b[self.k - 1] == 'v':
          if self.ends("ive"): pass
          else: return
      elif self.b[self.k - 1] == 'z':
          if self.ends("ize"): pass
          else: return
      else:
          return
      if self.m() > 1:
          self.k = self.j

  def step5(self):
      """step5() removes a final -e if m() > 1, and changes -ll to -l if
      m() > 1.
      """
      self.j = self.k
      if self.b[self.k] == 'e':
          a = self.m()
          if a > 1 or (a == 1 and not self.cvc(self.k-1)):
              self.k = self.k - 1
      if self.b[self.k] == 'l' and self.doublec(self.k) and self.m() > 1:
          self.k = self.k -1

  def stem(self, p, i=None, j=None):
      """In stem(p,i,j), p is a char pointer, and the string to be stemmed
      is from p[i] to p[j] inclusive. Typically i is zero and j is the
      offset to the last character of a string, (p[j+1] == '\0'). The
      stemmer adjusts the characters p[i] ... p[j] and returns the new
      end-point of the string, k. Stemming never increases word length, so
      i <= k <= j. To turn the stemmer into a module, declare 'stem' as
      extern, and delete the remainder of this file.
      """
      if i is None:
          i = 0
      if j is None:
          j = len(p) - 1
      # copy the parameters into statics
      self.b = p
      self.k = j
      self.k0 = i
      if self.k <= self.k0 + 1:
          return self.b # --DEPARTURE--

      # With this line, strings of length 1 or 2 don't go through the
      # stemming process, although no mention is made of this in the
      # published algorithm. Remove the line to match the published
      # algorithm.

      self.step1ab()
      self.step1c()
      self.step2()
      self.step3()
      self.step4()
      self.step5()
      return self.b[self.k0:self.k+1]
if __name__ == '__main__':
    p = PorterStemmer()
    if len(sys.argv) > 1:
        for f in sys.argv[1:]:
            infile = open(f, 'r')
            while 1:
                output = ''
                word = ''
                line = infile.readline()
                if line == '':
                    break
                for c in line:
                    if c.isalpha():
                        word += c.lower()
                    else:
                        if word:
                            output += p.stem(word, 0,len(word)-1)
                            word = ''
                        output += c.lower()
                print output,
            infile.close()