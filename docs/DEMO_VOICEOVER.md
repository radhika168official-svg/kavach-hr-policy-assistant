# Demo voiceover script

The narrated video is `demo/Kavach_HR_Assistant_Demo.mp4` (4:00). The narration was generated with the Windows
text-to-speech voice "Microsoft Zira". To use your own voice instead, read each line at its start time; every
line fits before the next one starts. (Spoken spellings such as "K V 1 0 0 1" and "H R B P" were written for
the TTS engine; say them naturally.)

| Start | Narration |
|---|---|
| 0:00 | This is the Kavach HR Policy Assistant: a prototype that answers employees' HR questions only from the Kavach policy pack, personalised using the employee roster. Policy numbers come from deterministic rules, so they can't be invented, and every answer cites its policy section. |
| 0:20 | First, Aarav, employee K V 1 0 0 1. He is Band A, in a corporate role, based in Mumbai. |
| 0:32 | He asks for his hotel limit in Pune. Pune is a Tier 1 city, so Band A gets 3,500 rupees a night, citing section 3 point 1. |
| 0:42 | Now Priya, K V 1 0 0 2, a Band M manager, asks exactly the same question. |
| 0:52 | Same question, different answer: 5,500 rupees a night, because she is Band M. |
| 1:01 | If she doesn't say which city, the assistant doesn't guess. It asks one short follow-up question. |
| 1:10 | She says Indore, a Tier 2 or 3 city, so her limit is 4,000 rupees. |
| 1:18 | Then a follow-up in the same chat: and for Pune? The assistant remembers the topic and answers for Pune. |
| 1:28 | Gym membership is not in the policy pack. So the assistant says it doesn't know, and points her to her H R B P, Ananya Ghosh, with her email. No policy is invented. |
| 1:42 | Asking about another employee's band is refused. The assistant never shares other employees' records. |
| 1:52 | A prompt injection attempt, telling it to ignore its rules, is refused too, and logged. |
| 1:58 | Next, an employee I D that isn't in the roster. The user can continue, but the assistant asks for details whenever an answer depends on them. |
| 2:11 | Daily allowance depends on band, so it asks for the band instead of guessing. |
| 2:18 | With Band M, the answer is 900 rupees per day of travel. |
| 2:23 | Now a sensitive message. Kavya, K V 1 0 0 6, whose H R B P is Vikram Rao. |
| 2:34 | She reports harassment by a colleague. The assistant does not judge or give advice. It shares the Internal Committee route: the email address, the three month timeline, confidentiality, and protection from retaliation. A confidential POSH alert is logged, without the details of her message. |
| 2:52 | Next, Arjun, K V 1 0 0 7, shares that he is struggling. |
| 3:02 | The assistant responds with care, shares the Employee Assistance Programme helpline, and raises an urgent alert so that his H R B P can check in with him. |
| 3:16 | This is the H R B P flag review page. It reads the alerts log, with urgent alerts first. |
| 3:24 | Filtering to Vikram Rao shows the POSH alert, routed to the Internal Committee, with him named for support. |
| 3:31 | And these are the raw C S V logs written during this demo. Every message and reply is recorded with a timestamp, session, employee I D, topic, flag type and H R B P routing. The harassment message itself is withheld. |
| 3:45 | All six sample questions pass, and 73 automated tests pass. The optional language model only ever picks a topic label. It never writes the answer. Thank you for watching. |
