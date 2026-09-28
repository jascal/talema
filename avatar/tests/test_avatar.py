import io
import json
import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dialogue
from tts import (_word_phonemes, cues_from_durations, is_word, talema_to_ipa,
                 talema_words, tokens, word_spans)

def sample_suggestions(tree):
    return [
        {'tree':tree,'en':'Four is two plus two.','es':'Cuatro es dos más dos.','de':'Vier ist zwei plus zwei.'},
        {'tree':{'root':'velom','children':[]},'en':'Welcome.','es':'Bienvenido.','de':'Willkommen.'},
    ]

class AvatarTests(unittest.TestCase):
    # A stand-in for Kokoro's vocabulary. It deliberately contains the space character,
    # because the real one does: the model receives the gaps between words and they
    # shift every later word's timing if the span walk ignores them.
    vocab = set('abdefhiklmnopstuvɡɾˈ. ')

    def setUp(self):
        pass

    def _stream(self, text):
        """The phoneme stream the model actually receives: every character of the
        phonemized sentence that the vocabulary knows, spaces included."""
        return [c for c in talema_to_ipa(text) if c in self.vocab]
    def test_trees(self):
        dialogue.validate_speech('bi fura pe si tova tova .')
        for text in ['bi fura pe .', 'bi fura pe si tova tova tova .', 'hello world .', 'bi fura pe si tova tova']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                dialogue.validate_speech(text)

    def test_timings_cover_audio_without_overrun(self):
        cues, word_cues = cues_from_durations(list('pao'), [2,3,5,4,2], 1.6)
        self.assertEqual([c['shape'] for c in cues], ['closed','open','round'])
        self.assertAlmostEqual(cues[0]['start'], .2)
        self.assertAlmostEqual(cues[-1]['end'], 1.4)
        self.assertTrue(all(a['end']==b['start'] for a,b in zip(cues,cues[1:])))
        # No source words supplied: no per-word cues are produced.
        self.assertEqual(word_cues, [])
        with self.assertRaises(RuntimeError):
            cues_from_durations(['a'], [1,2], 1)

    def test_word_cues_follow_phoneme_spans(self):
        # Spans are (start, end) indices into the phoneme stream: first word 'pa',
        # second word 'oa'.
        cues, word_cues = cues_from_durations(list('paoa'), [1,2,3,4,5,1], 3.0,
                                              spans=[(0,2),(2,4)])
        self.assertEqual(len(word_cues), 2)
        self.assertAlmostEqual(word_cues[0]['start'], cues[0]['start'])
        self.assertAlmostEqual(word_cues[0]['end'], cues[1]['end'])
        self.assertAlmostEqual(word_cues[1]['start'], cues[2]['start'])
        self.assertAlmostEqual(word_cues[1]['end'], cues[3]['end'])
        # Every word cue sits inside the audio duration.
        self.assertTrue(all(0 <= c['start'] <= c['end'] <= 3.0 for c in word_cues))

    def test_spans_cover_every_word_exactly_once(self):
        for text in ['bi fura 25 pe si tova tova .',
                     'nu ja-me topi .',
                     'veloma . voni te topike vasa pe tada .']:
            with self.subTest(text=text):
                spoken = tokens(text)
                words = [token for token in spoken if is_word(token)]
                stream = self._stream(text)
                spans = word_spans(spoken, self.vocab)
                self.assertEqual(len(spans), len(words))
                # A span can never run past the stream the model actually receives.
                self.assertTrue(all(end <= len(stream) for _, end in spans))
                # And each word's phonemes are exactly the slice it claims.
                for word, (start, end) in zip(words, spans):
                    expected = [c for c in _word_phonemes(word).replace(' ', '')
                                if c in self.vocab]
                    self.assertEqual(stream[start:end], expected)

    def test_spans_skip_characters_the_model_does_not_voice(self):
        # Digits are dropped from the phoneme stream, so they must not advance the
        # cursor; the word after a number has to start where the number would, plus
        # the two spaces that surround it.
        spoken = tokens('bi 25 pe')
        self.assertEqual([t for t in spoken if is_word(t)], ['bi', '25', 'pe'])
        self.assertEqual(word_spans(spoken, self.vocab), [(0, 2), (3, 3), (4, 6)])

    def test_spans_skip_sentence_punctuation(self):
        # The period between two sentences is voiced but belongs to no word, so the
        # second sentence must not be shifted by it: "veloma . voni ." spends two
        # phonemes (period, space) on the gap that the cursor has to step over.
        spoken = tokens('veloma . voni .')
        spans = word_spans(spoken, self.vocab)
        self.assertEqual(spans, [(0, 7), (10, 15)])

    def test_hyphenated_words_are_spoken_and_highlighted(self):
        self.assertEqual(talema_words('nu ja-me topi .'), ['nu', 'ja-me', 'topi'])

    def test_unvoiced_word_gets_a_zero_width_cue_in_place(self):
        # A word with no surviving phonemes still advances the subtitle in step,
        # rather than collapsing to the start of the audio.
        cues, word_cues = cues_from_durations(list('bia'), [1, 2, 3, 4, 1], 2.0,
                                              spans=[(0, 2), (2, 2)])
        self.assertAlmostEqual(word_cues[0]['start'], cues[0]['start'])
        self.assertAlmostEqual(word_cues[0]['end'], cues[1]['end'])
        self.assertAlmostEqual(word_cues[1]['start'], cues[2]['start'])
        self.assertAlmostEqual(word_cues[1]['end'], word_cues[1]['start'])

    def test_bare_vowel_reply_recovers_through_the_repair(self):
        # The observed failure: asked to say a letter, the model puts the letter in
        # `root` and the turn dies. The retry must produce speakable Talema.
        letter = [{'root': 'a', 'children': []}]
        # "vanam is the name of the first vowel" — the ordinal is spoken, so the
        # caption's "first" is earned.
        named = [{'root': 'kar', 'children': [{'root': 'vanam', 'children': []},
                                               {'root': 'vokel', 'children': [{'root': 'fir', 'children': []}]}]}]
        suggestions = [{'tree': {'root': 'vonam', 'children': []}, 'en': 'The fourth vowel.',
                        'es': 'La cuarta vocal.', 'de': 'Der vierte Vokal.'},
                       {'tree': {'root': 'fir', 'children': [{'root': 'vokel', 'children': []}]},
                        'en': 'The first vowel.', 'es': 'La primera vocal.', 'de': 'Der erste Vokal.'}]
        def response(trees, en):
            data = {'trees': trees, 'suggestions': suggestions, 'en': en, 'es': en,
                    'de': en, 'emotion': 'warm', 'turn_move': 'ask_followup'}
            return io.BytesIO(json.dumps({'status': 'completed', 'output': [
                {'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(data)}]}]}).encode())
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test', 'TALEMA_MODEL': 'test-model'}), \
             patch('urllib.request.urlopen', side_effect=[response(letter, 'A.'),
                                                          response(named, 'The first vowel is called vanam.')]) as call:
            result = dialogue.reply('Say the letter a for me.', [])
            repair = json.loads(call.call_args_list[1].args[0].data)['input'][-1]['content']
        # It spoke, and what it said is a valid sentence.
        self.assertEqual(result['talema'], 'kari vanama vokele fira .')
        dialogue.validate_speech(result['talema'])
        self.assertIn('vanam', repair)
        # 'u' is the ending for four dependents, never a root, and stripping vowels
        # off a bare vowel leaves nothing for the whole-word recovery to recover.
        for vowel in 'aeiou':
            with self.subTest(root=vowel):
                with self.assertRaises(ValueError):
                    dialogue.serialize_tree({'root': vowel, 'children': []})
        self.assertEqual(dialogue.ending(4), 'u')
        repair = dialogue.root_repair("Unknown dictionary root: 'u'")
        self.assertIn("'u' is an ending, not a root", repair)
        self.assertIn('no root is a bare vowel', repair)
        # The generic advice is still present, so the older test's expectations hold.
        self.assertIn('bare-root field', repair)
        self.assertIn('Do not repeat the invalid root', repair)
        # A whole-word slip gets the generic advice without the vowel explanation.
        self.assertNotIn('is an ending', dialogue.root_repair("Unknown dictionary root: 'buke'"))

    def test_bare_vowel_repair_names_the_word_for_that_vowel(self):
        # The model reaches for a written letter when asked to say one. The repair has
        # to hand it the root the book actually uses, or it simply fails again.
        self.assertEqual(dialogue.vowel_name('a'), 'vanam')
        self.assertEqual(dialogue.vowel_name('o'), 'vonam')
        self.assertEqual(dialogue.vowel_name('u'), 'vunam')
        self.assertIsNone(dialogue.vowel_name('x'))
        repair = dialogue.root_repair("Unknown dictionary root: 'a'")
        self.assertIn("'a' is an ending, not a root", repair)
        self.assertIn("'vanam'", repair)
        self.assertIn('A written letter cannot be spoken', repair)
        # A whole-word slip must not be handed a vowel name.
        self.assertNotIn('vanam', dialogue.root_repair("Unknown dictionary root: 'buke'"))

    def test_persona_rules_out_bare_vowel_roots(self):
        self.assertIn('No root is ever a bare vowel', dialogue.PERSONA)
        self.assertIn('endings, not roots', dialogue.PERSONA)
        self.assertIn('A written letter is not a root either', dialogue.PERSONA)
        for root in ('vanam', 'venam', 'vinam', 'vonam', 'vunam'):
            self.assertIn(f'`{root}`', dialogue.PERSONA)

    def test_cache_key_covers_the_persona_and_the_books(self):
        # Both halves of the cached prefix are hashed, so editing either busts the key.
        import hashlib
        expected = 'talema-tutor-' + hashlib.sha256(
            (dialogue.PERSONA + dialogue.BOOK).encode('utf-8')).hexdigest()[:16]
        self.assertEqual(dialogue.CACHE_KEY, expected)

    def test_caption_that_enumerates_unsaid_letters_is_rejected(self):
        # The reported case: Luma said "five vowels" and the English appended the
        # list, so the caption described more than the speech.
        talema = 'bi vokela fiva . vone ti pe tada te vokela .'
        caption = 'Talema has five vowels: a, e, i, o, and u. Would you like to practice a vowel?'
        self.assertTrue(dialogue.caption_adds_content(caption, talema))
        with self.assertRaises(dialogue.CaptionError):
            dialogue.check_caption('en', caption, talema)

    def test_caption_check_does_not_reject_ordinary_captions(self):
        talema = 'bi vokela fiva . vone ti pe tada te vokela .'
        # Same content, no invented list.
        dialogue.check_caption('en', 'Five vowels. Would you like to practise one?', talema)
        # Longer captions are normal: Talema is denser than English.
        dialogue.check_caption('en', 'Talema has five vowels. Would you like to practise one of them '
                                      'and hear how each one sounds?', talema)
        # A dictionary line that legitimately enumerates is not generated speech, but
        # it must not be what trips the check on its own either.
        self.assertFalse(dialogue.caption_adds_content('Four is two and two.', 'bi fura pe si tova tova .'))

    def test_persona_prefers_concrete_elaboration(self):
        self.assertIn('Be concrete rather than categorical', dialogue.PERSONA)
        self.assertIn('say its members or give\none specific example', dialogue.PERSONA)
        # One sentence per sentence, and no sentence of the caption's own.
        self.assertIn('Every sentence in the Talema gets one sentence in the caption', dialogue.PERSONA)
        self.assertIn('the caption has no sentence of its own', dialogue.PERSONA)
        self.assertIn('If a sentence is worth saying, say it in Talema', dialogue.PERSONA)

    def test_order_word_may_ride_inside_a_coined_root(self):
        # vonam glosses as "vowel-fourth", so saying vonama really does convey
        # "fourth" even though no ordinal root is spoken on its own.
        self.assertEqual(dialogue.unsupported_order('The fourth vowel.', 'vonama .'), '')
        self.assertEqual(dialogue.unsupported_order('The first vowel.', 'vanama .'), '')
        # A coined root for a different vowel does not license the word.
        self.assertEqual(dialogue.unsupported_order('The first vowel.', 'vonama .'), 'first')

    def test_caption_may_not_invent_a_sentence(self):
        # Observed: the Talema said "Hi. What topic do you want?" and the caption
        # answered with three sentences, one of which Luma never spoke.
        talema = 'habola . vase topike vone pe tada .'
        caption = 'Hello! You can greet me with "hello." Which topic would you like to explore?'
        self.assertEqual(dialogue.count_sentences(talema), 2)
        self.assertEqual(dialogue.count_sentences(caption), 3)
        self.assertTrue(dialogue.caption_adds_a_sentence(caption, talema))
        with self.assertRaises(dialogue.CaptionError) as caught:
            dialogue.check_caption('en', caption, talema)
        self.assertIn('may not contain a sentence', str(caught.exception))
        # The faithful caption for the same speech passes.
        dialogue.check_caption('en', 'Hello! Which topic do you want?', talema)

    def test_sentence_count_ignores_markers(self):
        # The book's own claim marks ("Proved:", "Seen:", "Open:") head a sentence the
        # Talema already carries, so they are stripped before counting.
        self.assertEqual(dialogue.count_sentences('Proved: two and two are four. We have a proof.'), 2)
        self.assertEqual(dialogue.count_sentences('One sentence.'), 1)
        self.assertEqual(dialogue.count_sentences(''), 0)

    def test_a_decimal_point_is_not_a_sentence_boundary(self):
        self.assertEqual(dialogue.count_sentences('The test takes 0.7 seconds. It works.'), 2)
        self.assertEqual(dialogue.count_sentences('Version 1.8 follows 2.0.'), 1)
        self.assertEqual(dialogue.count_sentences('Version 1.8 follows 3.14 and 0.001.'), 1)
        # But a full stop straight after a number still ends a sentence: the book uses
        # 0.7, 1.8, 3.14 and 0.001, so the exemption has to be decimals and nothing more.
        self.assertEqual(dialogue.count_sentences('The answer is 4. Try again.'), 2)

    def test_nothing_after_a_dash_is_hidden_from_the_count(self):
        # A slash or dash never hides the rest of a caption. Four attempts to treat one
        # as a restatement marker were each defeated by a caption that reads as a
        # restatement and is not one, the last being "Sleep. - Do not sleep." -- every
        # content word shared, and the opposite claim. So nothing is folded: every
        # sentence after a dash is counted, however short and however much it repeats.
        for text, want in (
            ('Welcome - practice now. Say hello.', 2),        # dash mid-sentence
            ('Welcome / practice now. Say hello.', 2),
            ('Welcome — let us begin. You can greet me with hello.', 2),
            ('Welcome. - Practice now.', 2),                  # dash after a finished
            ('Welcome. - Practice now. - Say hello.', 3),     # ...sentence, twice over
            ('The test passes. - We are not done yet.', 2),
            ('The answer is four. - The answer holds.', 2),   # shares a word, adds one
            ('Welcome. - Say hi.', 2),                        # all words under four letters
            ('Welcome. / Try it.', 2),
            ('Sleep. - Do not sleep.', 2),                    # repeats, and negates
            ('Der Präsident. - Nach der Tagesordnung folgt die gemeinsame Aussprache (Dok.', 2),
        ):
            with self.subTest(text=text):
                self.assertEqual(dialogue.count_sentences(text), want)
                # Each must also be caught against a one-sentence speech, or the added
                # sentence would pass validation outright.
                self.assertTrue(dialogue.caption_adds_a_sentence(text, 'veloma .'))
        # Division is a slash and carries no full stop either way.
        self.assertEqual(dialogue.count_sentences('12 / 4 = 3'), 1)

    def test_a_restatement_is_not_guessed_at(self):
        # The book writes one utterance two ways on a few lines. The counter does not try
        # to recognise that, because it cannot be done from words, so these are counted
        # for the two sentences they are. They are declared in the parity test below.
        for text in ('Please sleep. / Sleep!', 'Por favor, duerme. - ¡Duerme!',
                     'Sleep. - Do not sleep.'):
            with self.subTest(text=text):
                self.assertEqual(dialogue.count_sentences(text), 2)
        # These are already one sentence, with no full stop inside the alternatives.
        for text in ('I see a dog / dogs.', 'The dog sleeps / slept / will sleep.'):
            with self.subTest(text=text):
                self.assertEqual(dialogue.count_sentences(text), 1)

    def test_a_quote_closes_its_sentence_without_counting_twice(self):
        # English and German write the full stop inside the quotation marks, so the
        # closing quote is the only terminator. Blanking the span would run the
        # sentence into the next one and under-count.
        self.assertEqual(dialogue.count_sentences('Kant said: "Never lie." He meant it.'), 2)
        self.assertEqual(dialogue.count_sentences('Kant said: "Never lie."'), 1)
        # A quote inside a sentence is not a boundary at all.
        self.assertEqual(dialogue.count_sentences('Er sagte "hallo" und ging.'), 1)
        # The quoted text is a sentence in its own right and has to stay countable:
        # blanking it left punctuation with nothing behind it, and both counted as zero.
        self.assertEqual(dialogue.count_sentences('"Hello." "Goodbye."'), 2)
        self.assertEqual(dialogue.count_sentences('She said "Hello." Then she left.'), 2)

    def test_sentence_parity_holds_on_the_published_books(self):
        # The invariant this check rests on, asserted so it cannot quietly rot.
        #
        # Two lines are the book's own restatements: it writes one utterance two ways
        # ("Please sleep. / Sleep!", and the Spanish the translator renders
        # "Por favor, duerme. - ¡Duerme!"), so those captions hold one sentence more
        # than the Talema they translate. They are named here rather than absorbed by a
        # rule in the counter, because any shape that folds them also folds
        # "Sleep. - Do not sleep." — which repeats every content word and says the
        # opposite. Naming them keeps the exception visible and checkable by hand; a
        # silent tolerance would hide the drift this test exists to catch.
        restated = {'Please sleep. / Sleep!', 'Por favor, duerme. - ¡Duerme!'}
        rows = [json.loads(line) for line in
                Path(__file__).resolve().parents[2].joinpath('data/sentences.jsonl')
                .read_text(encoding='utf-8').splitlines() if line.strip()]
        for lang, field in (('en', 'en'), ('de', 'de_mt'), ('es', 'es_mt')):
            checked = [r for r in rows if r.get(field, '').strip()]
            over = [r[field] for r in checked
                    if dialogue.count_sentences(r[field]) > dialogue.count_sentences(r['talema'])]
            under = [r[field] for r in checked
                     if dialogue.count_sentences(r[field]) < dialogue.count_sentences(r['talema'])]
            self.assertEqual(sorted(over), sorted(restated & set(over)),
                             f'{lang} captions invent a sentence: {sorted(set(over) - restated)[:5]}')
            self.assertEqual(under, [], f'{lang} captions drop a sentence: {under[:5]}')
            self.assertGreater(len(checked), 1500, f'{lang} corpus unexpectedly small')
        # Both exceptions are still exactly one sentence more, not a drifting pair.
        for caption in restated:
            self.assertEqual(dialogue.count_sentences(caption), 2)

    def test_caption_may_not_add_an_order_the_speech_lacks(self):
        # Observed: the Talema asked which vowel, and the caption volunteered
        # "which would you like to explore next".
        talema = 'bee vokela . rake kase vokela .'
        caption = 'These are the vowels. Which of these would you like to look at next?'
        self.assertEqual(dialogue.unsupported_order(caption, talema), 'next')
        with self.assertRaises(dialogue.CaptionError) as caught:
            dialogue.check_caption('en', caption, talema)
        self.assertIn('does not say it', str(caught.exception))

    def test_order_check_covers_every_caption_language(self):
        # Spanish and German must be caught too, or the tutor just elaborates in them.
        talema = 'bi vokela . rake kase vokela .'
        for lang, caption, expected in [
                ('en', 'These are the vowels. Which one next?', 'next'),
                ('es', 'Estas son las vocales. ¿Cuál siguiente?', 'siguiente'),
                ('de', 'Das sind die Vokale. Welches als Nächstes?', 'nächste')]:
            with self.subTest(lang=lang):
                self.assertEqual(dialogue.unsupported_order(caption, talema, lang), expected)
                with self.assertRaises(dialogue.CaptionError):
                    dialogue.check_caption(lang, caption, talema)
        # The order words come from the lexicon's own de/es columns, not a hardcoded list.
        for lang, word in (('es', 'cuarto'), ('es', 'último'), ('de', 'vierte'), ('de', 'fünfte')):
            self.assertIn(word, dialogue.ORDER[lang])

    def test_english_order_words_are_matched_exactly(self):
        # Stem matching is for inflected languages only: "against" is not "again".
        self.assertEqual(dialogue.unsupported_order('It ran against the mill.',
                                                    'runi gone muhile la pe pesa .'), '')

    def test_sentence_count_handles_spanish_punctuation(self):
        talema = 'habola . vase topike vone pe tada .'
        self.assertTrue(dialogue.caption_adds_a_sentence(
            '¡Hola! Puedes saludarme con "hola". ¿Qué tema quieres?', talema))
        self.assertFalse(dialogue.caption_adds_a_sentence('¡Hola! ¿Qué tema quieres?', talema))

    def test_order_check_accepts_any_synonym_root(self):
        # first is fir, fis or rimer; last is lasat, lat, latim or sulet. A caption
        # whose order is carried by any of them is faithful.
        self.assertEqual(dialogue.unsupported_order('Learn them first.', 'feni te tara fisa .'), '')
        self.assertEqual(dialogue.unsupported_order('Learn them first.', 'feni te tara fira .'), '')
        self.assertEqual(dialogue.unsupported_order('The last vowel counts ones.',
                                                    'saheni te pona pe vokeli lata la .'), '')
        # And a caption with no order word is untouched.
        self.assertEqual(dialogue.unsupported_order('Four is two and two.',
                                                    'bi fura pe si tova tova .'), '')

    def test_order_check_is_quiet_on_the_published_books(self):
        # Calibrated against data/sentences.jsonl in every caption language, so it does
        # not reject the corpus.
        rows = [json.loads(line) for line in
                Path(__file__).resolve().parents[2].joinpath('data/sentences.jsonl')
                .read_text(encoding='utf-8').splitlines() if line.strip()]
        rows = [r for r in rows if r.get('en', '').strip()]
        for lang, key in (('en', 'en'), ('es', 'es_mt'), ('de', 'de_mt')):
            subset = [r for r in rows if r.get(key, '').strip()]
            flagged = [r[key] for r in subset if dialogue.unsupported_order(r[key], r['talema'], lang)]
            with self.subTest(lang=lang):
                self.assertLess(len(flagged), len(subset) * 0.005,
                                f'order check too eager on the {lang} book: {flagged[:3]}')

    def test_caption_repair_points_at_speaking_not_deleting(self):
        self.assertTrue(issubclass(dialogue.CaptionError, ValueError))
        long_es = ('Talema tiene cinco vocales: a, e, i, o y u. '
                   '¿Te gustaría practicar una de ellas ahora?')
        with self.assertRaises(dialogue.CaptionError) as caught:
            dialogue.check_caption('es', long_es, 'bi vokela fiva . vone ti pe tada te vokela .')
        self.assertIn('say more in Talema', str(caught.exception))

    def test_response_and_caption_separation(self):
        tree={'root':'b','children':[{'root':'fur','children':[]},{'root':'p','children':[
              {'root':'s','children':[{'root':'tov','children':[]},{'root':'tov','children':[]}]}]}]}
        data={'trees':[tree],'suggestions':sample_suggestions(tree),
              'en':'Four is two plus two.','es':'Cuatro es dos más dos.','de':'Vier ist zwei plus zwei.',
              'emotion':'warm','turn_move':'ask_topic'}
        response={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(data)}]}]}
        with patch.dict(os.environ, {'OPENAI_API_KEY':'test','TALEMA_MODEL':'test-model'}), patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(response).encode())) as call:
            result=dialogue.reply('veloma', [])
            body=json.loads(call.call_args.args[0].data)
        self.assertEqual(result['talema'],'bi fura pe si tova tova .')
        self.assertEqual(result['en'],data['en'])
        self.assertEqual(result['suggestions'],[
            {'talema':'bi fura pe si tova tova .','en':'Four is two plus two.','es':'Cuatro es dos más dos.','de':'Vier ist zwei plus zwei.'},
            {'talema':'veloma .','en':'Welcome.','es':'Bienvenido.','de':'Willkommen.'},
        ])
        self.assertFalse(body['store'])
        self.assertEqual(body['input'][-1]['content'],'veloma')
        self.assertTrue(body['text']['format']['strict'])
        # every book is in the cached prefix, and the prefix is routed by a key that tracks the books' content
        for name in ('BUKE_DE_LORE_FIRA.md','logic.md','physics.md','philosophy.md','morality.md','digital.md','mathematics.md'):
            self.assertIn(name, body['instructions'])
        self.assertEqual(body['prompt_cache_key'], dialogue.CACHE_KEY)

    def test_start_uses_book_greeting_without_model(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY':'','TALEMA_MODEL':''}), patch('urllib.request.urlopen') as call:
            result=dialogue.reply('', [], start=True)
        call.assert_not_called()
        self.assertEqual(result['source'],'core book greeting and topic question')

    def test_start_is_led_by_model_when_configured(self):
        tree={'root':'b','children':[{'root':'fur','children':[]},{'root':'p','children':[
              {'root':'s','children':[{'root':'tov','children':[]},{'root':'tov','children':[]}]}]}]}
        data={'trees':[tree],'suggestions':sample_suggestions(tree),
              'en':'Four is two and two.','es':'Cuatro es dos y dos.','de':'Vier ist zwei und zwei.',
              'emotion':'warm','turn_move':'ask_topic'}
        response={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(data)}]}]}
        with patch.dict(os.environ, {'OPENAI_API_KEY':'test','TALEMA_MODEL':'test-model'}), patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(response).encode())) as call:
            result=dialogue.reply('', [], start=True)
            body=json.loads(call.call_args.args[0].data)
        self.assertEqual(result['source'],'test-model')
        self.assertEqual(body['input'][-1]['content'], dialogue.OPENING)

    def test_nested_trees_spell_their_own_endings(self):
        four={'root':'b','children':[{'root':'fur','children':[]},{'root':'p','children':[
              {'root':'s','children':[{'root':'tov','children':[]},{'root':'tov','children':[]}]}]}]}
        self.assertEqual(dialogue.serialize_trees([four]), 'bi fura pe si tova tova .')
        self.assertEqual(dialogue.ending(5), 'ea')
        with self.assertRaises(ValueError):
            dialogue.serialize_tree({'root':'notaroot','children':[]})

    def test_inflected_word_forms_in_root_slot_are_recovered(self):
        self.assertEqual(dialogue.serialize_tree({'root':'buke','children':[]}), 'buka .')
        self.assertEqual(dialogue.serialize_tree({'root':'de','children':[]}), 'da .')
        self.assertEqual(dialogue.serialize_tree({'root':'lore','children':[]}), 'lora .')

    def test_model_reply_is_spelled_from_nested_tree(self):
        tree={'root':'b','children':[{'root':'fur','children':[]},{'root':'p','children':[
              {'root':'s','children':[{'root':'tov','children':[]},{'root':'tov','children':[]}]}]}]}
        data={'trees':[tree],'suggestions':sample_suggestions(tree),
              'en':'Four is two and two.','es':'Cuatro es dos y dos.','de':'Vier ist zwei und zwei.',
              'emotion':'warm','turn_move':'ask_topic'}
        response={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(data)}]}]}
        with patch.dict(os.environ, {'OPENAI_API_KEY':'test','TALEMA_MODEL':'test-model'}), patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(response).encode())) as call:
            result=dialogue.reply('hola', [])
            body=json.loads(call.call_args.args[0].data)
        self.assertEqual(result['talema'], 'bi fura pe si tova tova .')
        self.assertIn('$defs', body['text']['format']['schema'])

    def test_unknown_root_repair_explains_bare_root_form(self):
        valid={'trees':[{'root':'b','children':[]}],
               'suggestions':sample_suggestions({'root':'b','children':[]}),
               'en':'Four.','es':'Cuatro.','de':'Vier.','emotion':'warm','turn_move':'ask_topic'}
        invalid=dict(valid, trees=[{'root':'zqx','children':[]}])
        def response(data):
            return io.BytesIO(json.dumps({'status':'completed','output':[{'type':'message','content':[
                {'type':'output_text','text':json.dumps(data)}]}]}).encode())
        with patch.dict(os.environ, {'OPENAI_API_KEY':'test','TALEMA_MODEL':'test-model'}), \
             patch('urllib.request.urlopen', side_effect=[response(invalid),response(valid)]) as call:
            result=dialogue.reply('hello', [])
            repair=json.loads(call.call_args_list[1].args[0].data)['input'][-1]['content']
        self.assertEqual(result['talema'],'ba .')
        self.assertIn('bare-root field',repair)
        self.assertIn('Do not repeat the invalid root',repair)

    def test_short_rate_limit_is_waited_out_once(self):
        import urllib.error
        from email.message import Message
        headers=Message(); headers['Retry-After']='2'
        limited=urllib.error.HTTPError('u',429,'rate',headers,io.BytesIO(json.dumps({'error':{'code':'rate_limit_exceeded','message':'try again in 2s'}}).encode()))
        tree={'root':'b','children':[{'root':'fur','children':[]},{'root':'p','children':[
              {'root':'s','children':[{'root':'tov','children':[]},{'root':'tov','children':[]}]}]}]}
        data={'trees':[tree],'suggestions':sample_suggestions(tree),
              'en':'Four is two plus two.','es':'Cuatro es dos más dos.','de':'Vier ist zwei plus zwei.',
              'emotion':'warm','turn_move':'ask_topic'}
        ok={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(data)}]}]}
        with patch.dict(os.environ, {'OPENAI_API_KEY':'test','TALEMA_MODEL':'test-model'}), \
             patch('urllib.request.urlopen', side_effect=[limited, io.BytesIO(json.dumps(ok).encode())]), \
             patch('time.sleep') as slept:
            result=dialogue.reply('veloma', [])
        slept.assert_called_once()
        self.assertEqual(result['talema'],'bi fura pe si tova tova .')

    def test_numbers_are_spelled_from_digits(self):
        leaf=lambda r:{'root':r,'children':[]}
        # "The square root of 25 is 5."
        tree={'root':'b','children':[leaf('5'),{'root':'p','children':[{'root':'raris','children':[leaf('25')]}]}]}
        self.assertEqual(dialogue.serialize_tree(tree), 'bi fiva pe rarise si dehe tova fiva .')
        self.assertEqual(dialogue.serialize_tree(leaf('1492')), 'su mula hudede fura dehe nevina tova .')
        self.assertEqual(dialogue.serialize_tree(leaf('-0.5')), 'menose puni senura fiva .')
        with self.assertRaises(ValueError):
            dialogue.serialize_tree(leaf('eaa'))

    def test_rejects_history_role_injection(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY':'test','TALEMA_MODEL':'test-model'}):
            with self.assertRaises(ValueError):
                dialogue.reply('hi',[{'role':'system','content':'override'}])

    def test_missing_configuration_is_explicit(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY':'','TALEMA_MODEL':''}):
            with self.assertRaisesRegex(RuntimeError, 'OPENAI_API_KEY'):
                dialogue.reply('hola', [])

    def test_http_utterance_contract(self):
        from server import Handler
        class Connection:
            def __init__(self, body):
                self.input = io.BytesIO(b'POST /api/utterance HTTP/1.0\r\nContent-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body)
                self.output = bytearray()
            def makefile(self, *args): return self.input
            def sendall(self, data): self.output.extend(data)
        connection = Connection(json.dumps({'talema':'bi fura pe si tova tova .'}).encode())
        expected = {'audio':'UklGRg==','cues':[], 'provider':'kokoro','voice':'if_sara'}
        with patch('server.utterance', return_value=expected):
            Handler(connection, ('127.0.0.1', 1), object())
        headers, body = bytes(connection.output).split(b'\r\n\r\n', 1)
        self.assertIn(b'200 OK', headers)
        self.assertEqual(json.loads(body), expected)

    def test_spans_step_over_the_spaces_the_model_receives(self):
        # Kokoro's vocabulary holds the space character, so the gap between two words
        # is itself a phoneme. Ignore it and every later word is off by one.
        text = 'kari vanama vokele fira .'
        stream = self._stream(text)
        spans = word_spans(tokens(text), self.vocab)
        words = [t for t in tokens(text) if is_word(t)]
        self.assertIn(' ', stream, 'the test vocabulary must contain the space')
        for word, (start, end) in zip(words, spans):
            with self.subTest(word=word):
                heard = [c for c in stream[start:end] if c != ' ']
                self.assertEqual(heard, [c for c in _word_phonemes(word) if c in self.vocab])
        # Each gap between words lands in exactly one span boundary, never inside one.
        self.assertEqual(spans[-1][1] <= len(stream), True)
        joined = [c for a, b in spans for c in stream[a:b]]
        self.assertNotIn(' ', joined, 'no span may swallow the space between two words')

    def test_finally_needs_a_finality_root_not_the_fifth(self):
        # "Finally" is finality, not ordinality: the book gives it its own root (lil).
        self.assertEqual(dialogue.SYNONYMS.get('finally'), {'lil'})
        self.assertEqual(dialogue.unsupported_order('Say it finally.', 'lila .'), '')
        self.assertEqual(dialogue.unsupported_order('Say it finally.', 'raka .'), 'finally')
        self.assertEqual(dialogue.unsupported_order('The fifth vowel.', 'vunama .'), '')
        # And the other two languages follow the same root, not the ordinal.
        self.assertEqual(dialogue.ORDER['de']['schließlich'], 'finally')
        self.assertEqual(dialogue.ORDER['es']['finalmente'], 'finally')
        self.assertEqual(dialogue.unsupported_order('Dímelo finalmente.', 'raka .', 'es'), 'finalmente')
        self.assertEqual(dialogue.unsupported_order('Sag es schließlich.', 'raka .', 'de'), 'schließlich')
        self.assertNotEqual(dialogue.ORDER['en'].get('finally'), 'fifth')

    def test_utterance_words_line_up_one_to_one_with_cues(self):
        # The client pairs word_cues[i] with the i-th highlighted word, so the two
        # lists must be the same length and advance together across sentences and
        # over characters the model never voices.
        import tts
        text = 'veloma . voni te 25 topike vasa pe tada .'
        def fake_kokoro(phonemes, token_list=None):
            spoken = token_list or []
            spans = word_spans(spoken, self.vocab)
            stream = [c for c in phonemes if c in self.vocab]
            cues, word_cues = cues_from_durations(stream, [1] * (len(stream) + 2),
                                                  float(len(stream)), spans)
            return b'RIFF', cues, word_cues
        with patch.object(tts, '_kokoro', side_effect=fake_kokoro):
            result = tts.utterance(text)
        self.assertEqual(result['words'], ['veloma', 'voni', 'te', '25', 'topike', 'vasa', 'pe', 'tada'])
        self.assertEqual(len(result['word_cues']), len(result['words']))
        cues = result['word_cues']
        # Ordered, non-overlapping, and never before the first phoneme cue.
        self.assertGreaterEqual(cues[0]['start'], result['cues'][0]['start'])
        for earlier, later in zip(cues, cues[1:]):
            self.assertLessEqual(earlier['end'], later['start'])
            self.assertLessEqual(earlier['start'], earlier['end'])

    def test_unknown_native_word_phonology(self):
        self.assertEqual(talema_to_ipa('rarise'), 'ˈɾaɾise')

    def test_opening_prompt_locks_out_the_format_example(self):
        # The persona's only fully-typed Talema sentence must be marked format-only,
        # so the model cannot echo it as its opening utterance.
        self.assertIn('never say it', dialogue.PERSONA)
        self.assertIn('bi fura pe si tova tova', dialogue.PERSONA)
        self.assertIn('example from these instructions', dialogue.PERSONA)
        # The OPENING must forbid echoing the example, ask for a say-back phrase,
        # and itself contain no concrete Talema sentence the tutor could parrot.
        self.assertIn('example from your instructions', dialogue.OPENING)
        self.assertIn('a fact, a number', dialogue.OPENING)
        self.assertIn('say back', dialogue.OPENING)
        self.assertNotIn('bi fura pe si tova tova', dialogue.OPENING)
        for sentence in dialogue.OPENING.split('.'):
            self.assertFalse(re.search(r'[a-z]{3,}\s+[a-z]+\.', sentence),
                              f'OPENING should not embed a concrete Talema sentence: {sentence!r}')

if __name__=='__main__': unittest.main()
