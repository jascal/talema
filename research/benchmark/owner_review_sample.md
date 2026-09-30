# Owner review sample: 123 of 1230 novel items (10%, stratified by frame)

Two separate questions per row.

1. **wrong?** Does the **English** say the same thing as the **tree**? (The tree is the authored form; the Talema
   text is its exact compilation; the blind reader's English is shown for reference.) Put `x` for any item that is wrong
   or that you dispute, write those ids to `owner_drops.txt`, then rerun `freeze.py`.
2. **odd?** Is the sentence semantic nonsense or too strange to be a fair example ("The temperature is yellow")? Put
   `x` if so. This does not remove the item; it tells us how much of the benchmark is odd, and lets the odd ones be
   reported as their own stratum.

| id | frame | English (intended) | tree | blind reader said | wrong? | odd? |
|---|---|---|---|---|---|---|
| dev-0001 | wh question | What do people make from stone? | `(make (OBJ what) (from stone) (SUBJ people))` | What do people make from stone? | | |
| dev-0011 | request | Please test the passion. | `(please (test/VERB (OBJ (passion the))))` | Please test the passion. | | |
| dev-0015 | copular | The shadow is the opposite of the artist. | `(be (opposite/ADJ (of (artist the)) the) (SUBJ (shadow the)))` | The shadow is opposite of the artist. | | |
| dev-0021 | declarative | They thank the theory. | `(thank/VERB (OBJ (theory the)) (SUBJ they))` | They thank the theory. | | |
| dev-0067 | wh question | Who needs the proof of the language? | `(need/VERB (OBJ (proof/NOUN (of (language/NOUN the)) the)) (SUBJ who))` | Who needs the proof of the language? | | |
| dev-0080 | negation | The creation does not involve a part. | `(involve/VERB (OBJ (part/NOUN a)) not (SUBJ (creation/NOUN the)))` | The creation does not involve a part. | | |
| dev-0102 | copular | The plate is new. | `(be new/ADJ (SUBJ (plate/NOUN the)))` | The plate is new. | | |
| dev-0111 | copular | The practice is interesting. | `(be interesting/ADJ (SUBJ (practice/NOUN the)))` | The practice is interesting. | | |
| dev-0118 | modal or tense | The conclusion will suffer. | `(suffer/VERB will/VERB (SUBJ (conclusion/NOUN the)))` | The conclusion will suffer. | | |
| dev-0121 | place or time | We strengthen the money. | `(strengthen/VERB (OBJ (money/NOUN the)) (SUBJ we))` | We strengthen the money. | | |
| dev-0126 | copular | The pause is quiet. | `(be quiet/ADJ (SUBJ (pause/NOUN the)))` | The pause is quiet. | | |
| dev-0145 | coordination | We play and the health surrounds us. | `(and (play/VERB (SUBJ we)) (surround/VERB (OBJ we) (SUBJ (health/NOUN the))))` | We play and the health surrounds us. | | |
| dev-0184 | declarative | I use my hand on the tree. | `(use/VERB (OBJ (hand/NOUN my)) (on (tree/NOUN the)) (SUBJ I))` | I use my hand on the tree. | | |
| dev-0193 | wh question | Who promotes the soup? | `(promote/VERB (OBJ (soup/NOUN the)) (SUBJ who))` | Who promotes the soup? | | |
| dev-0194 | subordination | I burn it because the identity depends. | `(burn/VERB (OBJ it) (because (depend/VERB (SUBJ (identity/NOUN the)))) (SUBJ I))` | I burn it because the identity depends. | | |
| dev-0199 | request | Please solve the annual kind. | `(please (solve/VERB (OBJ (kind/NOUN annual/ADJ the))))` | Please solve the annual kind. | | |
| dev-0204 | declarative | I wish for a game. | `(wish/VERB (for (game/NOUN a)) (SUBJ I))` | I wish for a game. | | |
| dev-0206 | negation | The grace does not seem zero. | `(seem/VERB (OBJ zero/NOUN) not (SUBJ (grace/NOUN the)))` | The grace does not seem zero. | | |
| dev-0208 | yes-no question | Do you drink the middle dream? | `(whether (drink/VERB (OBJ (dream/NOUN middle/ADJ the)) (SUBJ you)))` | Do you drink the middle dream? | | |
| dev-0224 | modal or tense | I will cook the content in the wind. | `(cook/VERB (OBJ (content/NOUN the)) will/VERB (in (wind/NOUN the)) (SUBJ I))` | I will cook the content in the wind. | | |
| dev-0245 | copular | The Olympic mind is a slave. | `(be (slave/NOUN a) (SUBJ (mind/NOUN olympic/ADJ the)))` | The Olympic mind is a slave. | | |
| dev-0252 | declarative | The example aims at a comeback. | `(aim/VERB (at (comeback/NOUN a)) (SUBJ (example/NOUN the)))` | The example aims at a comeback. | | |
| dev-0259 | declarative | The view starts the start. | `(start/VERB (OBJ (start/NOUN the)) (SUBJ (view/NOUN the)))` | The view starts the start. | | |
| dev-0274 | wh question | What does the mill prove about the meaning? | `(prove/VERB (OBJ what) (about (meaning/NOUN the)) (SUBJ (mill/NOUN the)))` | What does the mill prove about the meaning? | | |
| dev-0294 | possession | The same gram is left. | `(be left/NOUN (SUBJ (gram/NOUN same/ADJ the)))` | The same gram is left. | | |
| dev-0296 | declarative | I know the path of the computer. | `(know/VERB (OBJ (path/NOUN (of (computer/NOUN the)) the)) (SUBJ I))` | I know the path of the computer. | | |
| dev-0304 | yes-no question | Do you do the honest effect? | `(whether (do/VERB (OBJ (effect/NOUN honest/ADJ the)) (SUBJ you)))` | Do you do the honest effect? | | |
| dev-0311 | modal or tense | I will draw the choice of the input. | `(draw/VERB (OBJ (choice/NOUN (of (input/NOUN the)) the)) will/VERB (SUBJ I))` | I will draw the choice of the input. | | |
| dev-0321 | declarative | I name the equation of the layer. | `(name/VERB (OBJ (equation/NOUN (of (layer/NOUN the)) the)) (SUBJ I))` | I name the equation of the layer. | | |
| dev-0343 | subordination | I release the sequence when you call. | `(release/VERB (OBJ (sequence/NOUN the)) (when/SCONJ (call/VERB (SUBJ you))) (SUBJ I))` | I release the sequence when you call. | | |
| test-0007 | coordination | The representative loads and you want it. | `(and (load/VERB (SUBJ (representative/NOUN the))) (want/VERB (OBJ it) (SUBJ you)))` | The representative loads, and you want it. | | |
| test-0027 | yes-no question | Does the first individual take it? | `(whether (take/VERB (OBJ it) (SUBJ (individual/NOUN first/ADJ the))))` | Does the first individual take it? | | |
| test-0028 | copular | The fast start of the year is here. | `(be here (SUBJ (start/NOUN fast/ADJ (of (year/NOUN the)) the)))` | Here is the fast start of the year. | | |
| test-0040 | wh question | Who names the property at the party? | `(name/VERB (OBJ (property/NOUN the)) (at (party/NOUN the)) (SUBJ who))` | Who names the property at the party? | | |
| test-0042 | request | Please elevate the national technology. | `(please (elevate/VERB (OBJ (technology/NOUN national/ADJ the))))` | Please elevate the national technology. | | |
| test-0057 | possession | The human culture of humanity is mine. | `(be my (SUBJ (culture/NOUN human/ADJ (of humanity/NOUN) the)))` | The human culture of humanity is mine. | | |
| test-0061 | yes-no question | Do you remember the cheap journal? | `(whether (remember/VERB (OBJ (journal/NOUN cheap/ADJ the)) (SUBJ you)))` | Do you remember the cheap journal? | | |
| test-0062 | copular | The sort in the pan is tired. | `(be tired/ADJ (SUBJ (sort/NOUN the (in (pan/NOUN the)))))` | The sort in the pan is tired. | | |
| test-0093 | yes-no question | Does the sweet trouble reach you? | `(whether (reach/VERB (OBJ you) (SUBJ (trouble/NOUN sweet/ADJ the))))` | Does the sweet trouble reach you? | | |
| test-0103 | negation | I do not visit the leaf or the strawberry. | `(visit/VERB (OBJ (or (leaf/NOUN the) (strawberry/NOUN the))) not (SUBJ I))` | I do not visit the leaf or the strawberry. | | |
| test-0107 | declarative | I sing the hallucination of the time. | `(sing/VERB (OBJ (hallucination/NOUN (of (time/NOUN the)) the)) (SUBJ I))` | I sing the hallucination of the time. | | |
| test-0114 | request | Please drink in the small city. | `(please (drink/VERB (in (city/NOUN small/ADJ the))))` | Please drink in the small city. | | |
| test-0118 | wh question | Who brings the presentation of power? | `(bring/VERB (OBJ (presentation/NOUN (of power/NOUN) the)) (SUBJ who))` | Who brings the presentation of power? | | |
| test-0121 | request | Please destroy the easy side. | `(please (destroy/VERB (OBJ (side/NOUN easy/ADJ the))))` | Please destroy the easy side. | | |
| test-0122 | modal or tense | The wife will raise the definition. | `(raise/VERB (OBJ (definition/NOUN the)) will/VERB (SUBJ (wife/NOUN the)))` | The wife will raise the definition. | | |
| test-0139 | copular | The knife is sudden for the child. | `(be sudden/ADJ (for (child/NOUN the)) (SUBJ (knife/NOUN the)))` | The knife is sudden for the child. | | |
| test-0144 | possession | The black reason of the lie is mine. | `(be my (SUBJ (reason/NOUN black/ADJ (of (lie/NOUN the)) the)))` | My reason is the black reason of the lie. | | |
| test-0164 | yes-no question | Does the central partner emerge? | `(whether (emerge/VERB (SUBJ (partner/NOUN central/ADJ the))))` | Does the central partner emerge? | | |
| test-0177 | modal or tense | The bill will differ from the composition. | `(differ/VERB will/VERB (from (composition/NOUN the)) (SUBJ (bill/NOUN the)))` | The bill will differ from the composition. | | |
| test-0202 | copular | The senior speaker is an agent. | `(be (agent/NOUN a) (SUBJ (speaker/NOUN senior/ADJ the)))` | The senior speaker is an agent. | | |
| test-0209 | negation | The tower does not help the lane. | `(help/VERB (OBJ (lane/NOUN the)) not (SUBJ (tower/NOUN the)))` | The tower does not help the lane. | | |
| test-0227 | wh question | Who associates the support with the coin? | `(associate/VERB (OBJ (support/NOUN the)) (with (coin/NOUN the)) (SUBJ who))` | Who associates the support with the coin? | | |
| test-0232 | modal or tense | The row will present the store. | `(present/VERB (OBJ (store/NOUN the)) will/VERB (SUBJ (row/NOUN the)))` | The row will present the store. | | |
| test-0244 | number or quantity | Zero holy duties are here. | `(be here (SUBJ (duty/NOUN holy/ADJ zero/NUM)))` | There is no holy duty here. | | |
| test-0250 | negation | I do not predict the mercy or the courage. | `(predict/VERB (OBJ (or (mercy/NOUN the) (courage/NOUN the))) not (SUBJ I))` | I do not predict the mercy or the courage. | | |
| test-0253 | place or time | The contribution of the male sounds here. | `(sound/VERB here (SUBJ (contribution/NOUN (of (male/NOUN the)) the)))` | The contribution of the male sounds here. | | |
| test-0275 | place or time | I return to the house in the spring. | `(return/VERB (to/ADP (house/NOUN the)) (in (spring/NOUN the)) (SUBJ I))` | I return to the house in the spring. | | |
| test-0283 | copular | The sour representation is health. | `(be health/NOUN (SUBJ (representation/NOUN sour/ADJ the)))` | The sour representation is health. | | |
| test-0307 | declarative | The sum deceives me tomorrow. | `(deceive/VERB (OBJ I) tomorrow/NOUN (SUBJ (sum/NOUN the)))` | The sum deceives me tomorrow. | | |
| test-0322 | negation | I do not surrender the change for the apple. | `(surrender/VERB (OBJ (change/NOUN the)) (for (apple/NOUN the)) not (SUBJ I))` | I do not surrender the change for the apple. | | |
| test-0334 | subordination | I fry the skin when you restart. | `(fry/VERB (OBJ (skin/NOUN the)) (when/SCONJ (restart/VERB (SUBJ you))) (SUBJ I))` | I fry the skin when you restart. | | |
| test-0343 | place or time | The butterfly occupies the thought. | `(occupy/VERB (OBJ (thought/NOUN the)) (SUBJ (butterfly/NOUN the)))` | The butterfly occupies the thought. | | |
| test-0344 | copular | The true security of the democracy is here. | `(be here (SUBJ (security/NOUN true/ADJ (of (democracy/NOUN the)) the)))` | The true security of the democracy is here. | | |
| test-0356 | declarative | I hang the meal and the cake. | `(hang/VERB (OBJ (and (meal/NOUN the) (cake/NOUN the))) (SUBJ I))` | I hang the meal and the cake. | | |
| test-0358 | yes-no question | Do you use the global sand? | `(whether (use/VERB (OBJ (sand/NOUN global/ADJ the)) (SUBJ you)))` | Do you use the global sand? | | |
| test-0363 | number or quantity | Two blue ids are here. | `(be here (SUBJ (id/NOUN blue/ADJ two/NUM)))` | Two blue ids are here. | | |
| test-0372 | modal or tense | I will turn the noodle in the salad. | `(turn/VERB (OBJ (noodle/NOUN the)) will/VERB (in (salad/NOUN the)) (SUBJ I))` | I will turn the noodle in the salad. | | |
| test-0379 | subordination | I cover the morality when you travel. | `(cover/VERB (OBJ (morality/NOUN the)) (when/SCONJ (travel/VERB (SUBJ you))) (SUBJ I))` | I cover the morality when you travel. | | |
| test-0390 | modal or tense | The preposition will drift with the gun. | `(drift/VERB will/VERB (with (gun/NOUN the)) (SUBJ (preposition/NOUN the)))` | The preposition will drift with the gun. | | |
| test-0394 | modal or tense | I will count the flower at the source. | `(count/VERB (OBJ (flower/NOUN the)) will/VERB (at (source/NOUN the)) (SUBJ I))` | I will count the flower at the source. | | |
| test-0399 | negation | I do not guess the option of the mill. | `(guess/VERB (OBJ (option/NOUN (of (mill/NOUN the)) the)) not (SUBJ I))` | I do not guess the option of the mill. | | |
| test-0430 | place or time | I deliver the mine to the population. | `(deliver/VERB (OBJ (mine/NOUN the)) (to/ADP (population/NOUN the)) (SUBJ I))` | I deliver the mine to the population. | | |
| test-0441 | negation | The alert will not go with the cherry. | `(go/VERB will/VERB not (with (cherry/NOUN the)) (SUBJ (alert/NOUN the)))` | The alert will not go with the cherry. | | |
| test-0459 | possession | The private bone of the cruelty is mine. | `(be my (SUBJ (bone/NOUN private/ADJ (of (cruelty/NOUN the)) the)))` | The private bone of the cruelty is mine. | | |
| test-0481 | copular | The dry writer is a lie. | `(be (lie/NOUN a) (SUBJ (writer/NOUN dry/ADJ the)))` | The dry writer is a lie. | | |
| test-0487 | place or time | I request the unknown from God. | `(request/VERB (OBJ (unknown/NOUN the)) (from god/NOUN) (SUBJ I))` | I request the unknown from God. | | |
| test-0510 | subordination | I lie when you buy the pronoun. | `(lie/VERB (when/SCONJ (buy/VERB (OBJ (pronoun/NOUN the)) (SUBJ you))) (SUBJ I))` | I lie when you buy the pronoun. | | |
| test-0524 | modal or tense | I will choose the answer in the town. | `(choose/VERB (OBJ (answer/NOUN the)) will/VERB (in (town/NOUN the)) (SUBJ I))` | I will choose the answer in the town. | | |
| test-0526 | coordination | I wear the deduction and you install it. | `(and (wear/VERB (OBJ (deduction/NOUN the)) (SUBJ I)) (install/VERB (OBJ it) (SUBJ you)))` | I wear the deduction and you install it. | | |
| test-0532 | place or time | I pull the cost at the wage. | `(pull/VERB (OBJ (cost/NOUN the)) (at (wage/NOUN the)) (SUBJ I))` | I pull the cost at the wage. | | |
| test-0567 | subordination | I must go when the driver switches. | `(go must (when/SCONJ (switch/VERB (SUBJ (driver/NOUN the)))) (SUBJ I))` | I must go when the driver switches. | | |
| test-0595 | declarative | I intend the usage of the oil. | `(intend/VERB (OBJ (usage/NOUN (of (oil/NOUN the)) the)) (SUBJ I))` | I intend the usage of the oil. | | |
| test-0650 | place or time | I interpret the time of the symbol. | `(interpret/VERB (OBJ (time/NOUN (of (symbol/NOUN the)) the)) (SUBJ I))` | I interpret the time of the symbol. | | |
| test-0662 | subordination | I give you the bed when you find it. | `(give/VERB (OBJ (bed/NOUN the)) (DAT you) (when/SCONJ (find/VERB (OBJ it) (SUBJ you))) (SUBJ I))` | I give you the bed when you find it. | | |
| test-0682 | wh question | Why does the theory grow with the lack? | `(grow/VERB why (with (lack/NOUN the)) (SUBJ (theory/NOUN the)))` | Why does the theory grow with the lack? | | |
| test-0700 | place or time | I publish the year of travel. | `(publish/VERB (OBJ (year/NOUN (of travel/NOUN) the)) (SUBJ I))` | I publish the year of travel. | | |
| test-0705 | coordination | I kill the take and you want it. | `(and (kill/VERB (OBJ (take/NOUN the)) (SUBJ I)) (want/VERB (OBJ it) (SUBJ you)))` | I kill the take and you want it. | | |
| test-0712 | declarative | I love the hill and the water. | `(love/VERB (OBJ (and (hill/NOUN the) (water/NOUN the))) (SUBJ I))` | I love the hill and the water. | | |
| test-0718 | declarative | I warn the road about the meal. | `(warn/VERB (OBJ (road/NOUN the)) (about (meal/NOUN the)) (SUBJ I))` | I warn the road about the meal. | | |
| test-0728 | copular | The empty line is a princess. | `(be (princess/NOUN a) (SUBJ (line/NOUN empty/ADJ the)))` | The empty line is a princess. | | |
| test-0734 | declarative | The senator travels in the range. | `(travel/VERB (in (range/NOUN the)) (SUBJ (senator/NOUN the)))` | The senator travels in the range. | | |
| test-0738 | declarative | I wait at the circle for the meal. | `(wait/VERB (at (circle/NOUN the)) (for (meal/NOUN the)) (SUBJ I))` | I wait at the circle for the meal. | | |
| test-0750 | wh question | Which aspect will reach the goal? | `(reach/VERB (OBJ (goal/NOUN the)) will/VERB (SUBJ (aspect/NOUN which/DET)))` | Which aspect will reach the goal? | | |
| test-0751 | place or time | I memorize the conservation at the stone. | `(memorize/VERB (OBJ (conservation/NOUN the)) (at (stone/NOUN the)) (SUBJ I))` | I memorize the conservation at the stone. | | |
| test-0780 | yes-no question | Do you sit for the appropriate hour? | `(whether (sit/VERB (for (hour/NOUN appropriate/ADJ the)) (SUBJ you)))` | Do you sit for the appropriate hour? | | |
| test-0785 | request | Please call the slow train. | `(please (call/VERB (OBJ (train/NOUN slow/ADJ the))))` | Please call the slow train. | | |
| test-0791 | negation | The leadership will not have time. | `(have (OBJ time/NOUN) will/VERB not (SUBJ (leadership/NOUN the)))` | The leadership will not have time. | | |
| test-0804 | declarative | I wait at night for the current. | `(wait/VERB (for (current/NOUN the)) (in (night/NOUN the)) (SUBJ I))` | I wait for the current in the night. | | |
| test-0815 | wh question | How do you break the appearance of the water? | `(break/VERB (OBJ (appearance/NOUN (of (water/NOUN the)) the)) how (SUBJ you))` | How do you break the appearance of the water? | | |
| test-0829 | copular | The reality of the school is the opposite. | `(be (opposite/NOUN the) (SUBJ (reality/NOUN (of (school/NOUN the)) the)))` | The reality of the school is the opposite. | | |
| test-0848 | place or time | I hold the knife in the storm. | `(hold/VERB (OBJ (knife/NOUN the)) (in (storm/NOUN the)) (SUBJ I))` | I hold the knife in the storm. | | |
| test-0867 | subordination | I force the reference when you go. | `(force/VERB (OBJ (reference/NOUN the)) (when/SCONJ (go/VERB (SUBJ you))) (SUBJ I))` | I force the reference when you go. | | |
| test-0874 | coordination | I pay the indication and you will go. | `(and (pay/VERB (OBJ (indication/NOUN the)) (SUBJ I)) (go/VERB will/VERB (SUBJ you)))` | I pay the indication and you will go. | | |
| test-0875 | yes-no question | Do you fulfil the dead evening? | `(whether (fulfil/VERB (OBJ (evening/NOUN dead/ADJ the)) (SUBJ you)))` | Do you fulfil the dead evening? | | |
| test-0886 | copular | The primary theft is a credit. | `(be (credit/NOUN a) (SUBJ (theft/NOUN primary/ADJ the)))` | A credit is the primary theft. | | |
| test-0899 | coordination | I take the substance and you love it. | `(and (take/VERB (OBJ (substance/NOUN the)) (SUBJ I)) (love/VERB (OBJ it) (SUBJ you)))` | I take the substance and you love it. | | |
| test-0910 | declarative | I can use the plane. | `(use/VERB (OBJ (plane/NOUN the)) can (SUBJ I))` | I can use the plane. | | |
| test-0921 | declarative | I order the past of the form. | `(order/VERB (OBJ (past/NOUN (of (form/NOUN the)) the)) (SUBJ I))` | I order the past form. | | |
| test-0924 | place or time | I die in the function of the museum. | `(die/VERB (in (function/NOUN (of (museum/NOUN the)) the)) (SUBJ I))` | I die in the function of the museum. | | |
| test-0928 | request | Please express the question with care. | `(please (express/VERB (OBJ (question/NOUN the)) (with care/NOUN)))` | Please express the question with care. | | |
| test-0937 | declarative | I show the data of the cover. | `(show/VERB (OBJ (data/NOUN (of (cover/NOUN the)) the)) (SUBJ I))` | I show the data of the cover. | | |
| test-0950 | request | Please wake the universal coin. | `(please (wake/VERB (OBJ (coin/NOUN universal/ADJ the))))` | Please wake the universal coin. | | |
| test-0968 | subordination | I understand the organization when you travel. | `(understand/VERB (OBJ (organization/NOUN the)) (when/SCONJ (travel/VERB (SUBJ you))) (SUBJ I))` | I understand the organization when you travel. | | |
| test-0970 | negation | I cannot see the year of the symbol. | `(see/VERB (OBJ (year/NOUN (of (symbol/NOUN the)) the)) can not (SUBJ I))` | I can't see the year of the symbol. | | |
| test-0983 | request | Please touch the visible universe. | `(please (touch/VERB (OBJ (universe/NOUN visible/ADJ the))))` | Please touch the visible universe. | | |
| test-0984 | modal or tense | I will explain the product of the computer. | `(explain/VERB (OBJ (product/NOUN (of (computer/NOUN the)) the)) will/VERB (SUBJ I))` | I will explain the product of the computer. | | |
| test-0985 | wh question | Who shares the intention of the appearance? | `(share/VERB (OBJ (intention/NOUN (of (appearance/NOUN the)) the)) (SUBJ who))` | Who shares the intention of the appearance? | | |
| test-0990 | coordination | I know the cup and you follow it. | `(and (know/VERB (OBJ (cup/NOUN the)) (SUBJ I)) (follow/VERB (OBJ it) (SUBJ you)))` | I know the cup, and you follow it. | | |
| test-0998 | coordination | I comprise the poster and you deny it. | `(and (comprise/VERB (OBJ (poster/NOUN the)) (SUBJ I)) (deny/VERB (OBJ it) (SUBJ you)))` | I comprise the poster and you deny it. | | |
| test-1010 | declarative | The woman adds the couple. | `(add/VERB (OBJ (couple/NOUN the)) (SUBJ (woman/NOUN the)))` | The woman adds the couple. | | |
| test-1026 | declarative | The hunter releases the result. | `(release/VERB (OBJ (result/NOUN the)) (SUBJ (hunter/NOUN the)))` | The hunter releases the result. | | |
| test-1036 | yes-no question | Do you burn the second hour? | `(whether (burn/VERB (OBJ (hour/NOUN second/ADJ the)) (SUBJ you)))` | Do you burn the second hour? | | |
| test-1038 | subordination | I come when you download the treaty. | `(come/VERB (when/SCONJ (download/VERB (OBJ (treaty/NOUN the)) (SUBJ you))) (SUBJ I))` | I come when you download the treaty. | | |
