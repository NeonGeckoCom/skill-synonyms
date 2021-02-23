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
from mycroft.skills.core import MycroftSkill
from mycroft.skills.skill_data import read_vocab_file
from mycroft.util.log import LOG
from neon_utils import skill_needs_patching, stub_missing_parameters


class SynonymsSkill(MycroftSkill):
    def __init__(self):
        super(SynonymsSkill, self).__init__(name="SynonymSkill")
        self.syn_words = [word for w_list in read_vocab_file(self.find_resource('synonym.voc', 'vocab'))
                          for word in w_list]
        self.set_words = [word for w_list in read_vocab_file(self.find_resource('set.voc', 'vocab')) for word in w_list]
        self.for_words = [word for w_list in read_vocab_file(self.find_resource('for.voc', 'vocab')) for word in w_list]
        if skill_needs_patching(self):
            stub_missing_parameters(self)

    def initialize(self):
        self.make_active(-1)
        self.add_event('neon.change_synonym', self._handle_synonym_event)
        # TODO: Intent for removing synonyms DM

    def converse(self, message=None):
        utterances = message.data.get("utterances")
        LOG.debug(f"Check Synonyms: {utterances}")
        # Nothing to evaluate
        if not utterances:
            return False
        # Script command, don't try
        if message.context.get("cc_data", {}).get("execute_from_script"):
            return False
        try:
            handled_as_existing = self._check_utterance_is_synonym(message)
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

    def _handle_synonym_event(self, message):
        add = message.data.get("add")
        trigger = message.data.get("trigger")
        command = message.data.get("command")
        if add and trigger and command:
            self._add_synonym(message, trigger, command)

    def _parse_synonym_and_command_phrases(self, utterance: str) -> (str, str):
        """
        Try to parse out a synonym and command phrase from an incoming utterance
        :param utterance: Raw user utterance containing 'synonym' to evaluate
        :return: trigger_phrase, command_phrase parsed out of utterance or None
        """
        matched_syn_words = [word for word in utterance.split() if word in self.syn_words]

        try:
            trigger, command = utterance.split(f" {matched_syn_words[0]} ", 1)
            # Cleanup set/for vocab from detected phrases
            if trigger.split()[0] in self.set_words:
                trigger = " ".join(trigger.split()[1:])
            if command.split()[0] in self.for_words:
                command = " ".join(command.split()[1:])
            # Remove any trailing words in trigger phrase (as, a, etc)
            trigger_words = trigger.split()
            while self.voc_match(trigger_words[-1], "particles"):
                trigger_words.pop(-1)
            trigger = " ".join(trigger_words)
            # Return parsed trigger and command
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
            if not skill_prefs.get("synonyms"):
                skill_prefs["synonyms"] = {}

            # Check if spoken request is a valid synonym pair
            if trigger_phrase == command_phrase:
                self.speak_dialog('synonym_equals_command', {"syn_phrase": trigger_phrase,
                                                             "cmd_phrase": command_phrase}, private=True)
                return
            # Check if this exact synonym pair already exists
            if trigger_phrase in skill_prefs["synonyms"].get(command_phrase, []):
                self.speak_dialog('synonym_pair_already_exists', {"syn_phrase": trigger_phrase,
                                                                  "cmd_phrase": command_phrase}, private=True)
                return
            # Requested Trigger is already a Trigger
            if any([syns for syns in skill_prefs["synonyms"].values() if trigger_phrase in syns]):
                match = [x for x, y in skill_prefs["synonyms"].items() if trigger_phrase in y][0]
                self.speak_dialog('synonym_pair_already_exists', {"syn_phrase": trigger_phrase.title(),
                                                                  "cmd_phrase": match}, private=True)
                return
            # New command being aliased
            if command_phrase not in skill_prefs["synonyms"].keys():
                self.speak_dialog("new_synonym_command", {"syn_phrase": trigger_phrase,
                                                          "cmd_phrase": command_phrase}, private=True)
                trigger_phrases = [trigger_phrase]
            # Command has other triggers
            else:
                # New trigger already exists
                self.speak_dialog("add_synonym_command",
                                  {"syn_phrase": trigger_phrase,
                                   'already_filled': ", ".join(skill_prefs["synonyms"][command_phrase]),
                                   "cmd_phrase": command_phrase}, private=True)
                # LOG.info(trigger_phrase)
                # LOG.info(skill_prefs["synonyms"][command_phrase])
                trigger_phrases = skill_prefs["synonyms"][command_phrase]
                trigger_phrases.append(trigger_phrase)

            LOG.info(skill_prefs["synonyms"][command_phrase])
            updated_synonyms = {**skill_prefs["synonyms"],
                                **{command_phrase: trigger_phrases}}
            self.update_skill_settings({"synonyms": updated_synonyms}, message)
        except TypeError as e:
            LOG.error(f'Error adding {trigger_phrase} -> {command_phrase}')
            LOG.error(e)

    def _check_utterance_is_synonym(self, message):
        """
        Handler that filters incoming messages and checks if a synonym should be emitted in place of incoming utterance
        :param message: Incoming payload object
        """
        if message.data.get("utterances"):
            sentence = message.data.get('utterances')[0].lower()
            LOG.info(sentence)

            syn_exec_phrase = [x for x, y in self.preference_skill(message).get("synonyms", {}).items()
                               if sentence in [sentence.lower() for sentence in y]]
            LOG.debug(syn_exec_phrase)
        else:
            syn_exec_phrase = False
        LOG.info(syn_exec_phrase)
        if syn_exec_phrase and len(syn_exec_phrase) > 0:
            LOG.info(syn_exec_phrase)
            message.context["neon_should_respond"] = True
            self.bus.emit(message.forward("recognizer_loop:utterance", {"utterances": syn_exec_phrase,
                                                                        "lang": message.data.get("lang", "en-us")}))
            return True
        return False

    def stop(self):
        pass


def create_skill():
    return SynonymsSkill()
