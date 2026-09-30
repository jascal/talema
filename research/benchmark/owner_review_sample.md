# Owner review sample: 123 of 1230 novel items (10%, stratified by frame)

For each row: does the **English** say the same thing as the **tree**? (The tree is the authored form; the Talema
text is its exact compilation. The blind reader's English is shown for reference.) Put `x` in the last column for
any item that is wrong or that you dispute; write the ids to `owner_drops.txt`, then rerun `freeze.py`.

| id | frame | English (intended) | tree | blind reader said | wrong? |
|---|---|---|---|---|---|
| dev-0001 | wh question | What do people make from stone? | `(make (OBJ what) (from stone) (SUBJ people))` | What do people make from stone? | |
| dev-0015 | copular | The shadow is the opposite of the artist. | `(be (opposite/ADJ the (of (artist the))) (SUBJ (shadow the)))` | The shadow is opposite of the artist. | |
| dev-0021 | declarative | They thank the theory. | `(thank/VERB (OBJ (theory the)) (SUBJ they))` | They thank the theory. | |
| dev-0049 | wh question | How do you measure the secret? | `(measure/VERB (OBJ (secret/NOUN the)) how (SUBJ you))` | How do you measure the secret? | |
| dev-0067 | wh question | Who needs the proof of the language? | `(need/VERB (OBJ (proof/NOUN the (of (language/NOUN the)))) (SUBJ who))` | Who needs the proof of the language? | |
| dev-0080 | negation | The creation does not involve a part. | `(involve/VERB (OBJ (part/NOUN a)) not (SUBJ (creation/NOUN the)))` | The creation does not involve a part. | |
| dev-0102 | copular | The plate is new. | `(be new/ADJ (SUBJ (plate/NOUN the)))` | The plate is new. | |
| dev-0111 | copular | The practice is interesting. | `(be interesting/ADJ (SUBJ (practice/NOUN the)))` | The practice is interesting. | |
| dev-0118 | modal or tense | The conclusion will suffer. | `(suffer/VERB will/VERB (SUBJ (conclusion/NOUN the)))` | The conclusion will suffer. | |
| dev-0126 | copular | The pause is quiet. | `(be quiet/ADJ (SUBJ (pause/NOUN the)))` | The pause is quiet. | |
| dev-0145 | coordination | We play and the health surrounds us. | `(and (play/VERB (SUBJ we)) (surround/VERB (OBJ we) (SUBJ (health/NOUN the))))` | We play and the health surrounds us. | |
| dev-0184 | declarative | I use my hand on the tree. | `(use/VERB (OBJ (hand/NOUN my)) (on (tree/NOUN the)) (SUBJ I))` | I use my hand on the tree. | |
| dev-0194 | subordination | I burn it because the identity depends. | `(burn/VERB (OBJ it) (because (depend/VERB (SUBJ (identity/NOUN the)))) (SUBJ I))` | I burn it because the identity depends. | |
| dev-0199 | request | Please solve the annual kind. | `(please (solve/VERB (OBJ (kind/NOUN annual/ADJ the))))` | Please solve the annual kind. | |
| dev-0204 | declarative | I wish for a game. | `(wish/VERB (for (game/NOUN a)) (SUBJ I))` | I wish for a game. | |
| dev-0206 | negation | The grace does not seem zero. | `(seem/VERB (OBJ zero/NOUN) not (SUBJ (grace/NOUN the)))` | The grace does not seem zero. | |
| dev-0224 | modal or tense | I will cook the content in the wind. | `(cook/VERB will/VERB (OBJ (content/NOUN the)) (in (wind/NOUN the)) (SUBJ I))` | I will cook the content in the wind. | |
| dev-0245 | copular | The Olympic mind is a slave. | `(be (slave/NOUN a) (SUBJ (mind/NOUN olympic/ADJ the)))` | The Olympic mind is a slave. | |
| dev-0252 | declarative | The example aims at a comeback. | `(aim/VERB (at (comeback/NOUN a)) (SUBJ (example/NOUN the)))` | The example aims at a comeback. | |
| dev-0259 | declarative | The view starts the start. | `(start/VERB (OBJ (start/NOUN the)) (SUBJ (view/NOUN the)))` | The view starts the start. | |
| dev-0274 | wh question | What does the mill prove about the meaning? | `(prove/VERB (OBJ what) (about (meaning/NOUN the)) (SUBJ (mill/NOUN the)))` | What does the mill prove about the meaning? | |
| dev-0278 | yes-no question | Do you sell in the multiple city? | `(whether (sell/VERB (in (city/NOUN multiple/ADJ the)) (SUBJ you)))` | Do you sell in the multiple city? | |
| dev-0296 | declarative | I know the path of the computer. | `(know/VERB (OBJ (path/NOUN the (of (computer/NOUN the)))) (SUBJ I))` | I know the path of the computer. | |
| dev-0304 | yes-no question | Do you do the honest effect? | `(whether (do/VERB (OBJ (effect/NOUN honest/ADJ the)) (SUBJ you)))` | Do you do the honest effect? | |
| dev-0311 | modal or tense | I will draw the choice of the input. | `(draw/VERB will/VERB (OBJ (choice/NOUN the (of (input/NOUN the)))) (SUBJ I))` | I will draw the choice of the input. | |
| dev-0343 | subordination | I release the sequence when you call. | `(release/VERB (OBJ (sequence/NOUN the)) (when/SCONJ (call/VERB (SUBJ you))) (SUBJ I))` | I release the sequence when you call. | |
| test-0014 | place or time | I call about the law at the passport. | `(call/VERB (about (law/NOUN the)) (at (passport/NOUN the)) (SUBJ I))` | I call about the law at the passport. | |
| test-0015 | subordination | I think about the request because I aim. | `(think/VERB (about (request/NOUN the)) (because (aim/VERB (SUBJ I))) (SUBJ I))` | I think about the request because I aim. | |
| test-0024 | number or quantity | Twelve workouts are equal. | `(be equal/ADJ (SUBJ (workout/NOUN twelve/NUM)))` | Twelve workouts are equal. | |
| test-0065 | negation | The owner does not follow the land. | `(follow/VERB (OBJ (land/NOUN the)) not (SUBJ (owner/NOUN the)))` | The owner does not follow the land. | |
| test-0095 | place or time | I accept the bit of the man. | `(accept/VERB (OBJ (bit/NOUN the (of (man/NOUN the)))) (SUBJ I))` | I accept the bit of the man. | |
| test-0101 | coordination | I seek the mile and you beg. | `(and (seek/VERB (OBJ (mile/NOUN the)) (SUBJ I)) (beg/VERB (SUBJ you)))` | I seek the mile and you beg. | |
| test-0118 | wh question | Who brings the presentation of power? | `(bring/VERB (OBJ (presentation/NOUN the (of (power/NOUN)))) (SUBJ who))` | Who brings the presentation of power? | |
| test-0124 | negation | The resident does not laugh at fate. | `(laugh/VERB not (at (fate/NOUN)) (SUBJ (resident/NOUN the)))` | The resident does not laugh at fate. | |
| test-0154 | declarative | The philosopher links the attitude. | `(link/VERB (OBJ (attitude/NOUN the)) (SUBJ (philosopher/NOUN the)))` | The philosopher links the attitude. | |
| test-0164 | yes-no question | Does the central partner emerge? | `(whether (emerge/VERB (SUBJ (partner/NOUN central/ADJ the))))` | Does the central partner emerge? | |
| test-0166 | wh question | Who enters the set of the cooperation? | `(enter/VERB (OBJ (set/NOUN the (of (cooperation/NOUN the)))) (SUBJ who))` | Who enters the set of cooperation? | |
| test-0171 | yes-no question | Does the death produce a reasonable thing? | `(whether (produce/VERB (OBJ (thing/NOUN reasonable/ADJ a)) (SUBJ (death/NOUN the))))` | Does death produce a reasonable thing? | |
| test-0173 | possession | The high water of the father is mine. | `(be my (SUBJ (water/NOUN high/ADJ the (of (father/NOUN the)))))` | The father's high water is mine. | |
| test-0194 | copular | The hot stage is a journalist. | `(be (journalist/NOUN a) (SUBJ (stage/NOUN hot/ADJ the)))` | The hot stage is a journalist. | |
| test-0196 | declarative | I imagine the market of thinking. | `(imagine/VERB (OBJ (market/NOUN the (of (thinking/NOUN)))) (SUBJ I))` | I imagine the market of thinking. | |
| test-0201 | declarative | The pain provokes the pipe. | `(provoke/VERB (OBJ (pipe/NOUN the)) (SUBJ (pain/NOUN the)))` | The pain provokes the pipe. | |
| test-0208 | declarative | I search the post for the test. | `(search/VERB (OBJ (post/NOUN the)) (for (test/NOUN the)) (SUBJ I))` | I search the post for the test. | |
| test-0215 | wh question | Who views the union in the area? | `(view/VERB (OBJ (union/NOUN the)) (in (area/NOUN the)) (SUBJ who))` | Who views the union in the area? | |
| test-0271 | declarative | I mention the joy of the sky. | `(mention/VERB (OBJ (joy/NOUN the (of (sky/NOUN the)))) (SUBJ I))` | I mention the joy of the sky. | |
| test-0276 | coordination | The sentence arises and you buy it. | `(and (arise/VERB (SUBJ (sentence/NOUN the))) (buy/VERB (OBJ it) (SUBJ you)))` | The sentence arises and you buy it. | |
| test-0282 | copular | The professor is strange on the occasion. | `(be strange/ADJ (on (occasion/NOUN the)) (SUBJ (professor/NOUN the)))` | The professor is strange on the occasion. | |
| test-0283 | copular | The sour representation is health. | `(be health/NOUN (SUBJ (representation/NOUN sour/ADJ the)))` | The sour representation is health. | |
| test-0302 | modal or tense | The conjecture will limit the shell. | `(limit/VERB will/VERB (OBJ (shell/NOUN the)) (SUBJ (conjecture/NOUN the)))` | The conjecture will limit the shell. | |
| test-0313 | negation | I do not launch the mail in the sequence. | `(launch/VERB (OBJ (mail/NOUN the)) (in (sequence/NOUN the)) not (SUBJ I))` | I do not launch the mail in the sequence. | |
| test-0315 | coordination | I buy the motion and you suggest it. | `(and (buy/VERB (OBJ (motion/NOUN the)) (SUBJ I)) (suggest/VERB (OBJ it) (SUBJ you)))` | I buy the motion, and you suggest it. | |
| test-0325 | declarative | The fan travels with the constraint. | `(travel/VERB (with (constraint/NOUN the)) (SUBJ (fan/NOUN the)))` | The fan travels with the constraint. | |
| test-0330 | place or time | I eat the foundation in the content. | `(eat/VERB (OBJ (foundation/NOUN the)) (in (content/NOUN the)) (SUBJ I))` | I eat the foundation in the content. | |
| test-0342 | request | Please see the Indian council. | `(please (see/VERB (OBJ (council/NOUN indian/ADJ the))))` | Please see the Indian council. | |
| test-0371 | declarative | I purchase the personality of the failure. | `(purchase/VERB (OBJ (personality/NOUN the (of (failure/NOUN the)))) (SUBJ I))` | I purchase the personality of the failure. | |
| test-0385 | place or time | I initiate the wave at the bias. | `(initiate/VERB (OBJ (wave/NOUN the)) (at (bias/NOUN the)) (SUBJ I))` | I initiate the wave at the bias. | |
| test-0387 | declarative | I develop the peach and the stone. | `(develop/VERB (OBJ (and (peach/NOUN the) (stone/NOUN the))) (SUBJ I))` | I develop the peach and the stone. | |
| test-0398 | copular | The order is awesome. | `(be awesome/ADJ (SUBJ (order/NOUN the)))` | The order is awesome. | |
| test-0412 | subordination | I include the tale when you move. | `(include/VERB (OBJ (tale/NOUN the)) (when/SCONJ (move/VERB (SUBJ you))) (SUBJ I))` | I include the tale when you move. | |
| test-0414 | possession | The big hold of the equation is mine. | `(be my (SUBJ (hold/NOUN big/ADJ the (of (equation/NOUN the)))))` | The big hold of the equation is mine. | |
| test-0435 | yes-no question | Is the silent nucleus here? | `(whether (be here (SUBJ (nucleus/NOUN silent/ADJ the))))` | Is the silent nucleus here? | |
| test-0440 | wh question | Who plays the third vowel for the publisher? | `(play/VERB (OBJ (vowel-third/NOUN the)) (for (publisher/NOUN the)) (SUBJ who))` | Who plays the third vowel for the publisher? | |
| test-0444 | modal or tense | I will fetch the entropy of the part. | `(fetch/VERB will/VERB (OBJ (entropy/NOUN the (of (part/NOUN the)))) (SUBJ I))` | I will fetch the entropy of the part. | |
| test-0453 | declarative | The reduction of the prime acts. | `(act/VERB (SUBJ (reduction/NOUN the (of (prime/NOUN the)))))` | The reduction of the prime acts. | |
| test-0459 | possession | The private bone of the cruelty is mine. | `(be my (SUBJ (bone/NOUN private/ADJ the (of (cruelty/NOUN the)))))` | The private bone of the cruelty is mine. | |
| test-0465 | declarative | I build the revenue and the diff. | `(build/VERB (OBJ (and (revenue/NOUN the) (diff/NOUN the))) (SUBJ I))` | I build the revenue and the diff. | |
| test-0467 | yes-no question | Does the valid will stay? | `(whether (stay/VERB (SUBJ (will/NOUN valid/ADJ the))))` | Will the valid will stay? | |
| test-0488 | declarative | The text consists of the flower. | `(consist/VERB (of (flower/NOUN the)) (SUBJ (text/NOUN the)))` | The text consists of the flower. | |
| test-0500 | yes-no question | Do you make the decision independent? | `(whether (make/VERB (OBJ (decision/NOUN independent/ADJ the)) (SUBJ you)))` | Do you make the independent decision? | |
| test-0502 | place or time | I study the location of the percent. | `(study/VERB (OBJ (location/NOUN the (of (percent/NOUN the)))) (SUBJ I))` | I study the location of the percent. | |
| test-0504 | request | Please support the Russian truth. | `(please (support/VERB (OBJ (truth/NOUN russian/ADJ the))))` | Please support the Russian truth. | |
| test-0508 | yes-no question | Do you obtain the thirsty fact? | `(whether (obtain/VERB (OBJ (fact/NOUN thirsty/ADJ the)) (SUBJ you)))` | Do you obtain the thirsty fact? | |
| test-0524 | modal or tense | I will choose the answer in the town. | `(choose/VERB will/VERB (OBJ (answer/NOUN the)) (in (town/NOUN the)) (SUBJ I))` | I will choose the answer in the town. | |
| test-0530 | copular | The dramatic epoch is a timestamp. | `(be (timestamp/NOUN a) (SUBJ (epoch/NOUN dramatic/ADJ the)))` | The dramatic epoch is a timestamp. | |
| test-0548 | declarative | I capture the number in the format. | `(capture/VERB (OBJ (number/NOUN the)) (in (format/NOUN the)) (SUBJ I))` | I capture the number in the format. | |
| test-0550 | wh question | Where does the spoon travel with the disjunction? | `(travel/VERB where (with (disjunction/NOUN the)) (SUBJ (spoon/NOUN the)))` | Where does the spoon travel with the disjunction? | |
| test-0565 | negation | I do not look at the frequency of the apartment. | `(look/VERB (at (frequency/NOUN the (of (apartment/NOUN the)))) not (SUBJ I))` | I do not look at the frequency of the apartment. | |
| test-0585 | possession | The new growth of the future is mine. | `(be my (SUBJ (growth/NOUN new/ADJ the (of (future/NOUN the)))))` | The new growth of the future is mine. | |
| test-0593 | negation | I do not lay the pardon of the king. | `(lay/VERB (OBJ (pardon/NOUN the (of (king/NOUN the)))) not (SUBJ I))` | I do not lay the pardon of the king. | |
| test-0595 | declarative | I intend the usage of the oil. | `(intend/VERB (OBJ (usage/NOUN the (of (oil/NOUN the)))) (SUBJ I))` | I intend the usage of the oil. | |
| test-0599 | subordination | I build the man when you do it. | `(build/VERB (OBJ (man/NOUN the)) (when/SCONJ (do/VERB (OBJ it) (SUBJ you))) (SUBJ I))` | I build the man when you do it. | |
| test-0603 | copular | The second cash is a kind. | `(be (kind/NOUN a) (SUBJ (cash/NOUN second/ADJ the)))` | The second cash is a kind. | |
| test-0617 | copular | The feature of the leader is loud. | `(be loud/ADJ (SUBJ (feature/NOUN the (of (leader/NOUN the)))))` | The feature of the leader is loud. | |
| test-0624 | request | Please make the high earth. | `(please (make/VERB (OBJ (earth/NOUN high/ADJ the))))` | Please make the earth high. | |
| test-0629 | subordination | I count the legacy when you lose it. | `(count/VERB (OBJ (legacy/NOUN the)) (when/SCONJ (lose/VERB (OBJ it) (SUBJ you))) (SUBJ I))` | I count the legacy when you lose it. | |
| test-0644 | copular | The user is a transportation. | `(be (transportation/NOUN a) (SUBJ (user/NOUN the)))` | The user is a transportation. | |
| test-0646 | copular | The life of the number is slow. | `(be slow/ADJ (SUBJ (life/NOUN the (of (number/NOUN the)))))` | The life of the number is slow. | |
| test-0650 | place or time | I interpret the time of the symbol. | `(interpret/VERB (OBJ (time/NOUN the (of (symbol/NOUN the)))) (SUBJ I))` | I interpret the time of the symbol. | |
| test-0661 | subordination | I say that the achievement comprises it. | `(say/VERB (that/SCONJ (comprise/VERB (OBJ it) (SUBJ (achievement/NOUN the)))) (SUBJ I))` | I say that the achievement comprises it. | |
| test-0665 | coordination | I grasp the boyfriend and you make it. | `(and (grasp/VERB (OBJ (boyfriend/NOUN the)) (SUBJ I)) (make/VERB (OBJ it) (SUBJ you)))` | I grasp the boyfriend and you make it. | |
| test-0684 | coordination | I see the food and you find it. | `(and (see/VERB (OBJ (food/NOUN the)) (SUBJ I)) (find/VERB (OBJ it) (SUBJ you)))` | I see the food and you find it. | |
| test-0694 | place or time | I enjoy the holiday with the letter. | `(enjoy/VERB (OBJ (holiday/NOUN the)) (with (letter/NOUN the)) (SUBJ I))` | I enjoy the holiday with the letter. | |
| test-0698 | place or time | I keep the energy on the land. | `(keep/VERB (OBJ (energy/NOUN the)) (on (land/NOUN the)) (SUBJ I))` | I keep the energy on the land. | |
| test-0699 | subordination | I say the voice when you celebrate. | `(say/VERB (OBJ (voice/NOUN the)) (when/SCONJ (celebrate/VERB (SUBJ you))) (SUBJ I))` | I say the voice when you celebrate. | |
| test-0710 | subordination | I am the enemy when you compose. | `(be (enemy/NOUN the) (when/SCONJ (compose/VERB (SUBJ you))) (SUBJ I))` | I am the enemy when you compose. | |
| test-0719 | place or time | I check the duty in the grammar. | `(check/VERB (OBJ (duty/NOUN the)) (in (grammar/NOUN the)) (SUBJ I))` | I check the duty in the grammar. | |
| test-0723 | request | Please acquire the right article. | `(please (acquire/VERB (OBJ (article/NOUN right/ADJ the))))` | Please acquire the right article. | |
| test-0743 | negation | The faculty will not see the scene. | `(see/VERB (OBJ (scene/NOUN the)) will/VERB not (SUBJ (faculty/NOUN the)))` | The faculty will not see the scene. | |
| test-0795 | modal or tense | I will attend the day of the input. | `(attend/VERB will/VERB (OBJ (day/NOUN the (of (input/NOUN the)))) (SUBJ I))` | I will attend the day of the input. | |
| test-0798 | modal or tense | The athlete will cut the total. | `(cut/VERB will/VERB (OBJ (total/NOUN the)) (SUBJ (athlete/NOUN the)))` | The athlete will cut the total. | |
| test-0804 | declarative | I wait at night for the current. | `(wait/VERB (for (current/NOUN the)) (in (night/NOUN the)) (SUBJ I))` | I wait for the current in the night. | |
| test-0813 | place or time | I see the people at the personnel. | `(see/VERB (OBJ (people/NOUN the)) (at (personnel/NOUN the)) (SUBJ I))` | I see the people at the personnel. | |
| test-0821 | number or quantity | Four good works are here. | `(be here (SUBJ (work/NOUN good/ADJ four/NUM)))` | There are four good works here. | |
| test-0829 | copular | The reality of the school is the opposite. | `(be (opposite/NOUN the) (SUBJ (reality/NOUN the (of (school/NOUN the)))))` | The reality of the school is the opposite. | |
| test-0842 | modal or tense | The course will disappear in the college. | `(disappear/VERB will/VERB (in (college/NOUN the)) (SUBJ (course/NOUN the)))` | The course will disappear in the college. | |
| test-0865 | wh question | What do you think about the exception and the request? | `(think/VERB (OBJ what) (about (and (exception/NOUN the) (request/NOUN the))) (SUBJ you))` | What do you think about the exception and the request? | |
| test-0875 | yes-no question | Do you fulfil the dead evening? | `(whether (fulfil/VERB (OBJ (evening/NOUN dead/ADJ the)) (SUBJ you)))` | Do you fulfil the dead evening? | |
| test-0901 | subordination | I surround the house when you ignore it. | `(surround/VERB (OBJ (house/NOUN the)) (when/SCONJ (ignore/VERB (OBJ it) (SUBJ you))) (SUBJ I))` | I surround the house when you ignore it. | |
| test-0913 | declarative | The stranger answers in the market. | `(answer/VERB (in (market/NOUN the)) (SUBJ (stranger/NOUN the)))` | The stranger answers in the market. | |
| test-0924 | place or time | I die in the function of the museum. | `(die/VERB (in (function/NOUN the (of (museum/NOUN the)))) (SUBJ I))` | I die in the function of the museum. | |
| test-0926 | place or time | I feed the activist tomorrow. | `(feed/VERB (OBJ (activist/NOUN the)) tomorrow/NOUN (SUBJ I))` | I will feed the activist tomorrow. | |
| test-0928 | request | Please express the question with care. | `(please (express/VERB (OBJ (question/NOUN the)) (with (care/NOUN))))` | Please express the question with care. | |
| test-0931 | yes-no question | Does the different unit operate? | `(whether (operate/VERB (SUBJ (unit/NOUN different/ADJ the))))` | Does the different unit operate? | |
| test-0983 | request | Please touch the visible universe. | `(please (touch/VERB (OBJ (universe/NOUN visible/ADJ the))))` | Please touch the visible universe. | |
| test-0996 | request | Please want the big gas. | `(please (want/VERB (OBJ (gas/NOUN big/ADJ the))))` | Please want the big gas. | |
| test-0999 | request | Please fail the international enemy. | `(please (fail/VERB (OBJ (enemy/NOUN international/ADJ the))))` | Please fail the international enemy. | |
| test-1030 | wh question | What do you learn at the concert in the fall? | `(learn/VERB (OBJ what) (at (concert/NOUN the)) (in (fall/NOUN the)) (SUBJ you))` | What do you learn at the concert in the fall? | |
| test-1034 | coordination | I think of the people and you tell them. | `(and (think/VERB (about (people/NOUN the)) (SUBJ I)) (tell/VERB (OBJ they) (SUBJ you)))` | I think about the people and you tell them. | |
| test-1041 | modal or tense | I will write the pile of the district. | `(write/VERB will/VERB (OBJ (pile/NOUN the (of (district/NOUN the)))) (SUBJ I))` | I will write the pile of the district. | |
| test-1046 | negation | The president does not blame the square. | `(blame/VERB (OBJ (square/NOUN the)) not (SUBJ (president/NOUN the)))` | The president does not blame the square. | |
| test-1052 | negation | I do not do the work of the research. | `(do/VERB (OBJ (work/NOUN the (of (research/NOUN the)))) not (SUBJ I))` | I do not do the work of the research. | |
| test-1056 | coordination | I respond to the speech and you believe it. | `(and (respond/VERB (to/ADP (speech/NOUN the)) (SUBJ I)) (believe/VERB (OBJ it) (SUBJ you)))` | I respond to the speech and you believe it. | |
| test-1069 | modal or tense | I will prevent the acquisition of the condition. | `(prevent/VERB will/VERB (OBJ (acquisition/NOUN the (of (condition/NOUN the)))) (SUBJ I))` | I will prevent the acquisition of the condition. | |
