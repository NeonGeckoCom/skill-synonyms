# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
#
# Copyright 2008-2021 Neongecko.com Inc. | All Rights Reserved
#
# Notice of License - Duplicating this Notice of License near the start of any file containing
# a derivative of this software is a condition of license for this software.
# Friendly Licensing:
# No charge, open source royalty free use of the Neon AI software source and object is offered for
# educational users, noncommercial enthusiasts, Public Benefit Corporations (and LLCs) and
# Social Purpose Corporations (and LLCs). Developers can contact developers@neon.ai
# For commercial licensing, distribution of derivative works or redistribution please contact licenses@neon.ai
# Distributed on an "AS IS” basis without warranties or conditions of any kind, either express or implied.
# Trademarks of Neongecko: Neon AI(TM), Neon Assist (TM), Neon Communicator(TM), Klat(TM)
# Authors: Guy Daniels, Daniel McKnight, Regina Bloomstine, Elon Gasper, Richard Leeds
#
# Specialized conversational reconveyance options from Conversation Processing Intelligence Corp.
# US Patents 2008-2021: US7424516, US20140161250, US20140177813, US8638908, US8068604, US8553852, US10530923, US10530924
# China Patent: CN102017585  -  Europe Patent: EU2156652  -  Patents Pending
from mycroft import Message
from mycroft.skills.core import MycroftSkill  # , intent_handler
# from adapt.intent import IntentBuilder
from mycroft.skills.skill_data import read_vocab_file
from mycroft.util.log import LOG
# import re
# from mycroft.messagebus.message import Message


class SynonymsSkill(MycroftSkill):
    def __init__(self):
        super(SynonymsSkill, self).__init__(name="SynonymSkill")
        self.syn_words = [word for w_list in read_vocab_file(self.find_resource('synonym.voc', 'vocab'))
                          for word in w_list]
        self.set_words = [word for w_list in read_vocab_file(self.find_resource('set.voc', 'vocab')) for word in w_list]
        self.for_words = [word for w_list in read_vocab_file(self.find_resource('for.voc', 'vocab')) for word in w_list]

    def initialize(self):
        self.make_active(-1)
        # try:
        #     self.add_event('SS_new_syn', self._add_synonym)
        #     self.make_active(-1)
        # except Exception as e:
        #     LOG.error(e)

        # self.add_event('recognizer_loop:utterance', self.handle_syn_utterance)

    # @intent_handler(IntentBuilder("add_synonym").require("syn_phrase").require("cmd_phrase"))
    # def add_syn_intent(self, message):
    #     """
    #     Intent handler for "make `x` a synonym for `y`
    #     :param message: message object associated with request
    #     """
    #     # cmd_phrase, syn_phrase = '', ''
    #     LOG.info(message.data)
    #     syn_phrase = (message.data.get("syn_phrase"))
    #     cmd_phrase = message.data.get("cmd_phrase")
    #     self._add_synonym(message, syn_phrase, cmd_phrase)

    def _parse_synonym_and_command_phrases(self, utterance: str) -> (str, str):
        """
        Try to parse out a synonym and command phrase from an incoming utterance
        :param utterance: Raw user utterance containing 'synonym' to evaluate
        :return: trigger_phrase, command_phrase parsed out of utterance or None
        """
        matched_syn_words = [word for word in utterance.split() if word in self.syn_words]

        try:
            trigger, command = utterance.split(f" {matched_syn_words[0]} ", 1)
            if trigger.split()[0] in self.set_words:
                trigger = " ".join(trigger.split()[1:])
            if command.split()[0] in self.for_words:
                command = " ".join(command.split()[1:])

            # TODO: Voc match for these particles DM
            trigger_words = trigger.split()
            if trigger_words[-1] == "a":
                trigger_words.pop(-1)
            if trigger_words[-1] == "as":
                trigger_words.pop(-1)
            trigger = " ".join(trigger_words)
            if trigger and command:
                return trigger, command
        except Exception as e:
            LOG.error(e)
        return None

    def _add_synonym(self, message: Message, trigger_phrase: str, command_phrase: str):
        """
        Parse synonym and add to configuration
        :param message: Message associated with request
        :param trigger_phrase: Phrase to listen for
        :param command_phrase: Command to execute when syn_phrase is heard
        :return:
        """
        try:
            skill_prefs = self.preference_skill(message)
            # Check if spoken request is a valid synonym pair
            if trigger_phrase != command_phrase:

                # Requested Trigger already exists as a Command
                # TODO: Does this preclude it as a trigger?
                if trigger_phrase in skill_prefs.get("synonyms").keys():
                    self.speak_dialog('new_is_another_key', {"syn_phrase": trigger_phrase.title()}, private=True)
                    return
                # Requested Trigger is already a Trigger
                if trigger_phrase in skill_prefs.get("synonyms").values():
                    self.speak_dialog('new_is_another_value',
                                      {"syn_phrase": trigger_phrase.title(),
                                       "cmd_phrase": [x for x, y in
                                                      self.preference_skill(message).get("synonyms").items()
                                                      if trigger_phrase in y][0]}, private=True)
                    return
                # New command being aliased
                if command_phrase not in self.preference_skill(message).get("synonyms").keys():
                    self.speak_dialog("new_synonym", {"syn_phrase": trigger_phrase,
                                                      "cmd_phrase": command_phrase}, private=True)
                    # if not isinstance(trigger_phrase, list):
                    trigger_phrases = [trigger_phrase]
                # Command has other triggers
                else:
                    # New trigger already exists  TODO: This should be handled above already? DM
                    if trigger_phrase in self.preference_skill(message).get("synonyms")[command_phrase]:
                        self.speak_dialog('already_exists', {"syn_phrase": trigger_phrase.title(),
                                                             "cmd_phrase": command_phrase}, private=True)
                        return

                    self.speak_dialog("already_filled",
                                      {"syn_phrase": trigger_phrase,
                                       'already_filled': ", ".join(self.preference_skill(message).get("synonyms")
                                                                   [command_phrase]),
                                       "cmd_phrase": command_phrase}, private=True)
                    LOG.info(trigger_phrase)
                    LOG.info(self.preference_skill(message).get("synonyms")[command_phrase])
                    # if not isinstance(trigger_phrase, list):
                    #     trigger_phrase = [trigger_phrase]
                    trigger_phrases = [trigger_phrase]
                    trigger_phrases.extend(self.preference_skill(message).get("synonyms")[command_phrase])
                    # LOG.info(trigger_phrase)
                    LOG.info(self.preference_skill(message).get("synonyms")[command_phrase])
                # if not trigger_phrase and not command_phrase:
                #     raise TypeError

                updated_synonyms = {**skill_prefs.get("synonyms"),
                                    **{command_phrase: trigger_phrases}}
                self.update_skill_settings({"synonyms": updated_synonyms}, message)

            # This is not a valid spoken request
            else:
                self.speak_dialog('same_values', {"syn_phrase": trigger_phrase.title(),
                                                  "cmd_phrase": command_phrase}, private=True)
        except TypeError as e:
            LOG.error(f'Error adding {trigger_phrase} -> {command_phrase}')
            LOG.error(e)
            return

    def converse(self, message=None):
        utterances = message.data.get("utterances")
        LOG.debug(f"Check Synonyms: {utterances}")
        if not utterances:
            return False
        # TODO: Check for signal user running script and return false
        try:
            handled_as_existing = self.handle_syn_utterance(message)
            if handled_as_existing:
                return True
        except Exception as e:
            LOG.error(e)

        if self.voc_match(utterances[0], "synonym"):
            LOG.info(f"Potential New Synonym")
            phrases = self._parse_synonym_and_command_phrases(utterances[0])
            if phrases:
                self._add_synonym(message, phrases[0], phrases[1])
                return True
        return False

    def handle_syn_utterance(self, message):
        """
        Handler that filters incoming messages and checks if a synonym should be emitted in place of incoming utterance
        :param message: Incoming payload object
        """
        if message.data.get("utterances"):
            sentence = message.data.get('utterances')[0].lower()
            LOG.info(sentence)

            syn_exec_phrase = [x for x, y in self.preference_skill(message).get("synonyms").items()
                               if sentence in [sentence.lower() for sentence in y]]
            LOG.debug(syn_exec_phrase)
        else:
            syn_exec_phrase = False
        LOG.info(syn_exec_phrase)
        if syn_exec_phrase:
            LOG.info(syn_exec_phrase)
            message.context["neon_should_respond"] = True
            self.bus.emit(message.forward("recognizer_loop:utterance", {"utterances": syn_exec_phrase}))
            return True
        return False

    def stop(self):
        pass


def create_skill():
    return SynonymsSkill()
