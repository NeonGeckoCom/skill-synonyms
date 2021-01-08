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

from mycroft.skills.core import MycroftSkill, intent_handler
from adapt.intent import IntentBuilder
from mycroft.util.log import LOG
import re
from mycroft.messagebus.message import Message


class SynonymsSkill(MycroftSkill):
    def __init__(self):
        super(SynonymsSkill, self).__init__(name="SynonymSkill")

    def initialize(self):
        try:
            self.add_event('SS_new_syn', self._add_synonym)
            self.make_active(-1)
        except Exception as e:
            LOG.error(e)

        # self.add_event('recognizer_loop:utterance', self.handle_syn_utterance)

    @intent_handler(IntentBuilder("add_synonym").require("syn_phrase").require("cmd_phrase"))
    def add_syn_intent(self, message):
        """
        Intent handler for "make `x` a synonym for `y`
        :param message: message object associated with request
        """
        # cmd_phrase, syn_phrase = '', ''
        LOG.info(message.data)
        syn_phrase = (message.data.get("syn_phrase"))
        cmd_phrase = message.data.get("cmd_phrase")
        self._add_synonym(message, syn_phrase, cmd_phrase)

    def _add_synonym(self, message, syn_phrase=None, cmd_phrase=None):
        """
        Parse synonym and add to configuration
        :param message: message associated with request (
        :param syn_phrase: optional string phrase to listen for
        :param cmd_phrase: optional string command to execute when syn_phrase is heard
        :return:
        """
        try:
            pref_speech = self.preference_speech(message)

            LOG.debug(f"{message.data}, {message.context}")
            LOG.debug(f"{syn_phrase} => {cmd_phrase}")

            # Parse and add emitted synonyms (not skill intent)
            if not syn_phrase or not cmd_phrase:
                # This has a parsed pair from CC skill script
                if message.context.get("origin") == "custom-conversation.neon":
                    syn_phrases = message.data.get("cc_synonyms")  # List of synonyms
                    cmd_phrase = message.data.get("cmd_phrase")  # Command to execute on synonym
                    LOG.info(syn_phrases)
                    LOG.info(cmd_phrase)
                    # if isinstance(syn_phrase, list):
                    try:
                        # if new != self.user_info_available['speech']['synonyms'][existing]:
                        #     new.extend(self.user_info_available['speech']['synonyms'][existing])

                        # This list is different than the existing one, update config
                        if syn_phrases != pref_speech['synonyms'].get(cmd_phrase):
                            old_synonyms = pref_speech['synonyms'].get(cmd_phrase, [])
                            list(syn_phrases).extend(old_synonyms)
                            LOG.info(f"{cmd_phrase}: {syn_phrases}")
                            updated_synonyms = {**pref_speech['synonyms'], **{cmd_phrase: syn_phrases}}
                            LOG.debug(f"synonyms={updated_synonyms}")
                            if self.server:
                                user_dict = self.build_user_dict(message)
                                user_dict["synonyms"] = updated_synonyms
                                self.socket_io_emit(event="update profile", kind="skill",
                                                    flac_filename=message.context["flac_filename"], message=user_dict)
                            else:
                                # Update local synonyms dict
                                self.user_info_available["speech"]["synonyms"] = updated_synonyms
                                # Write file changes
                                self.user_config.update_yaml_file(header='speech', sub_header='synonyms',
                                                                  value=updated_synonyms)

                                # Don't need to emit because no other skill cares about synonyms
                                # self.bus.emit(Message('check.yml.updates',
                                #                       {"modified": ["ngi_user_info"]}, {"origin": "synonyms.neon"}))
                            # syn_phrase.extend(pref_speech['synonyms'][cmd_phrase])
                    except Exception as e:
                        LOG.error(e)

                # TODO Utterances are emitted pre-skills parsing and picked up here. Handle better DM
                else:
                    LOG.error(f"Got message in synonym intent: {message.data}")
                    LOG.info(message.data)
                    to_parse = message.data.get('utterances')[0]
                    LOG.info(to_parse)
                    pattern = re.compile(r'(make|set|add)\s+(?P<syn_phrase>.*)\sas (a|\s)+synonym\s+(to|for)\s+'
                                         r'(?P<cmd_phrase>.*)').finditer(to_parse)
                    for i in pattern:
                        syn_phrase = (i.group("syn_phrase")).rstrip()
                        cmd_phrase = (i.group("cmd_phrase")).rstrip()
                    LOG.info(syn_phrase)
                    LOG.info(cmd_phrase)
                    if not syn_phrase or not cmd_phrase:
                        pattern = re.compile(r'(make|set|add)\s+(?P<syn_phrase>.*)a(s a|s|\s)*\s+synonym\s+(to|for)\s+'
                                             r'(?P<cmd_phrase>.*)').finditer(to_parse)
                        for i in pattern:
                            syn_phrase = (i.group("syn_phrase")).rstrip()
                            cmd_phrase = (i.group("cmd_phrase")).rstrip()
                        LOG.info(syn_phrase)
                        LOG.info(cmd_phrase)
                    if not syn_phrase or not cmd_phrase:
                        LOG.info('Invalid request')
                        return

            # Check if spoken request is a valid synonym pair
            if syn_phrase != cmd_phrase:
                if syn_phrase in pref_speech['synonyms'].keys():
                    self.speak_dialog('new_is_another_key', {"syn_phrase": syn_phrase.title()}, private=True)
                    return
                if syn_phrase in pref_speech['synonyms'].values():
                    self.speak_dialog('new_is_another_value',
                                      {"syn_phrase": syn_phrase.title(),
                                       "cmd_phrase": [x for x, y in pref_speech['synonyms'].items()
                                                      if syn_phrase in y][0]}, private=True)
                    return
                if cmd_phrase not in pref_speech['synonyms'].keys():
                    self.speak_dialog("new_synonym", {"syn_phrase": syn_phrase,
                                                      "cmd_phrase": cmd_phrase}, private=True)
                    if not isinstance(syn_phrase, list):
                        syn_phrase = [syn_phrase]
                else:
                    if syn_phrase in pref_speech['synonyms'][cmd_phrase]:
                        self.speak_dialog('already_exists', {"syn_phrase": syn_phrase.title(),
                                                             "cmd_phrase": cmd_phrase}, private=True)
                        return

                    self.speak_dialog("already_filled",
                                      {"syn_phrase": syn_phrase,
                                       'already_filled': ", ".join(pref_speech['synonyms'][cmd_phrase]),
                                       "cmd_phrase": cmd_phrase}, private=True)
                    LOG.info(syn_phrase)
                    LOG.info(pref_speech['synonyms'][cmd_phrase])
                    if not isinstance(syn_phrase, list):
                        syn_phrase = [syn_phrase]
                    syn_phrase.extend(pref_speech['synonyms'][cmd_phrase])
                    LOG.info(syn_phrase)
                    LOG.info(pref_speech['synonyms'][cmd_phrase])
                if not syn_phrase and not cmd_phrase:
                    raise TypeError

                updated_synonyms = {**pref_speech['synonyms'], **{cmd_phrase: syn_phrase}}
                if self.server:
                    user_dict = self.build_user_dict(message)
                    user_dict["synonyms"] = updated_synonyms
                    self.socket_io_emit(event="update profile", kind="skill",
                                        flac_filename=message.context["flac_filename"], message=user_dict)
                else:
                    self.user_config.update_yaml_file(header='speech', sub_header='synonyms', value=updated_synonyms)
                    self.bus.emit(Message('check.yml.updates',
                                          {"modified": ["ngi_user_info"]}, {"origin": "synonyms.neon"}))

            # This is not a valid spoken request
            else:
                self.speak_dialog('same_values', {"syn_phrase": syn_phrase.title(),
                                                  "cmd_phrase": cmd_phrase}, private=True)
        except TypeError as e:
            LOG.error(f'Error adding {syn_phrase} -> {cmd_phrase}')
            LOG.error(e)
            return

    def converse(self, utterances, lang="en-us", message=None):
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
        # TODO: Try adding new synonym here? DM
        return False

    def handle_syn_utterance(self, message):
        """
        Handler that filters incoming messages and checks if a synonym should be emitted in place of incoming utterance
        :param message: Incoming payload object
        :return:
        """

        # TODO: Substitutions currently handled in listener
        if message.data.get("utterances"):
            sentence = message.data.get('utterances')[0]
            LOG.info(sentence)

            # if [x for x in ['make', 'set', 'add'] if x in sentence] and 'synonym' in sentence:
            #     payload = {
            #         'utterances': sentence,
            #         'flac_filename': message.context["flac_filename"]
            #     }
            #     self.bus.emit(Message("recognizer_loop:utterance", payload))

            LOG.info(message.data)
            pref_speech = self.preference_speech(message)
            LOG.info(pref_speech['synonyms'].items())
            syn_exists = [x for x, y in pref_speech['synonyms'].items()
                          if message.data.get('utterances')[0] in y
                          and message.data.get('utterances')[0] != x]
            # if not syn_exists:
            #     return False
        else:
            syn_exists = False
        LOG.info(syn_exists)
        if syn_exists:
            LOG.info(syn_exists)
            # audiofile = message.data.get("cc_data", {}).get("audio_file")
            # TODO: This should probably be a message.reply to preserve all context. DM
            # payload = message.context
            # payload['utterances'] = syn_exists
            # payload.get('cc_data', {})["execute_utterance"] = True
            message.context["neon_should_respond"] = True
            self.bus.emit(message.forward("recognizer_loop:utterance", {"utterances": syn_exists,
                                                                        "Neon": True}))
            return True
            # message.data["utterances"] = syn_exists
            # message.context.get("cc_data", {})["execute_utterance"] = True
            # payload = {
            #     'utterances': syn_exists,
            #     'flac_filename': message.context["flac_filename"],
            #     "cc_data": {"speak_execute": syn_exists,
            #                 "execute_utterance": True,
            #                 "audio_file": audiofile,
            #                 "raw_utterance": sentence
            #                 }
            # }
            # self.bus.emit(Message("recognizer_loop:utterance", payload))
        return False

    def stop(self):
        pass


def create_skill():
    return SynonymsSkill()
