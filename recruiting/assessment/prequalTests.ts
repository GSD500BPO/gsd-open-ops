// Prequalification test modules for the talent marketplace intake.
// Bilingual copy; questions are always answered in English (that is the job).

export interface MCQuestion {
  id: string;
  prompt: string;
  options: string[];
  correctIndex: number;
}

export const ENGLISH_QUESTIONS: MCQuestion[] = [
  {
    id: 'en1',
    prompt: 'The customer said he ____ for our call since 9 a.m.',
    options: ['is waiting', 'has been waiting', 'waits', 'was waited'],
    correctIndex: 1,
  },
  {
    id: 'en2',
    prompt: 'Choose the most professional way to open a cold call.',
    options: [
      'Hey, what\u2019s up? Got a sec?',
      'Hi, this is Ana with Acme Services \u2014 did I catch you at a bad time?',
      'Yes hello I am calling you for the offer.',
      'Hello sir, please listen me one minute.',
    ],
    correctIndex: 1,
  },
  {
    id: 'en3',
    prompt: 'If the prospect says "Send me an email," the best response is:',
    options: [
      'Okay, bye.',
      'Sure \u2014 what\u2019s the best address? And while I have you, what should I include so it\u2019s actually useful?',
      'No, I cannot do that.',
      'Email is not working, we only call.',
    ],
    correctIndex: 1,
  },
  {
    id: 'en4',
    prompt: 'Which sentence is grammatically correct?',
    options: [
      'I would of scheduled the appointment.',
      'I have schedule the appointment for Tuesday.',
      'I\u2019ve scheduled the appointment for Tuesday.',
      'I scheduling the appointment on Tuesday.',
    ],
    correctIndex: 2,
  },
  {
    id: 'en5',
    prompt: '"To follow up" means:',
    options: [
      'To end the conversation',
      'To contact again after a previous interaction',
      'To transfer the call',
      'To cancel a meeting',
    ],
    correctIndex: 1,
  },
  {
    id: 'en6',
    prompt: 'Pick the correct preposition: "I\u2019ll call you back ____ 3 p.m. Eastern."',
    options: ['on', 'in', 'at', 'to'],
    correctIndex: 2,
  },
  {
    id: 'en7',
    prompt: 'A homeowner says "We already have a water softener." The clearest reply is:',
    options: [
      'Okay, sorry to bother you.',
      'That\u2019s great \u2014 how long has it been in? Most units lose efficiency after about five years.',
      'Your softener is bad.',
      'I don\u2019t know about softeners, let me transfer you.',
    ],
    correctIndex: 1,
  },
  {
    id: 'en8',
    prompt: 'Which word best replaces "problem" in a customer call?',
    options: ['issue', 'disaster', 'mess', 'trouble maker'],
    correctIndex: 0,
  },
  {
    id: 'en9',
    prompt: 'Choose the correct past tense: "Yesterday I ____ 120 calls."',
    options: ['make', 'made', 'maked', 'have make'],
    correctIndex: 1,
  },
  {
    id: 'en10',
    prompt: '"ASAP" stands for:',
    options: [
      'As Simple As Possible',
      'After Sales And Payment',
      'As Soon As Possible',
      'Additional Sales Agent Program',
    ],
    correctIndex: 2,
  },
];

export const SALES_QUESTIONS: MCQuestion[] = [
  {
    id: 'sc1',
    prompt: 'A prospect books a demo but no-shows. What do you do first?',
    options: [
      'Mark the lead as dead.',
      'Call within 5 minutes, then send a reschedule link the same day.',
      'Wait one week and email.',
      'Send the proposal anyway.',
    ],
    correctIndex: 1,
  },
  {
    id: 'sc2',
    prompt: 'You have 200 dials to make and 40 warm inbound leads waiting. What comes first?',
    options: [
      'The 200 cold dials \u2014 volume wins.',
      'The 40 inbound leads \u2014 speed-to-lead beats cold volume.',
      'Update the CRM notes first.',
      'Ask the manager and wait.',
    ],
    correctIndex: 1,
  },
  {
    id: 'sc3',
    prompt: 'Best answer to "It\u2019s too expensive."',
    options: [
      'I can give you a discount right now.',
      'Compared to what? Let\u2019s look at what it costs to keep doing it the current way.',
      'Everyone says that.',
      'Okay, I\u2019ll call you next year.',
    ],
    correctIndex: 1,
  },
  {
    id: 'sc4',
    prompt: 'Which CRM entry is acceptable after a call?',
    options: [
      'called',
      'n/a',
      'Spoke with Mark (owner). Uses ServiceTitan, 6 techs, unhappy with lead volume. Demo set Thu 2 p.m. ET.',
      'no answer maybe later',
    ],
    correctIndex: 2,
  },
  {
    id: 'sc5',
    prompt: 'The client asks for something outside the agreed scope. You:',
    options: [
      'Do it quietly and hope nobody notices.',
      'Refuse and hang up.',
      'Acknowledge it, log it, and escalate to your account manager same day.',
      'Tell the client it is impossible.',
    ],
    correctIndex: 2,
  },
  {
    id: 'sc6',
    prompt: 'Your connect rate dropped 40% this week. First move?',
    options: [
      'Dial harder without changing anything.',
      'Check the data source, dial times, and caller-ID reputation before blaming the list.',
      'Ask for a new list immediately.',
      'Take the day off.',
    ],
    correctIndex: 1,
  },
];

export const TYPING_SAMPLE =
  'Thank you for calling Acme Services. My name is Ana and I will be helping you today. ' +
  'I see that your appointment is scheduled for Tuesday at two in the afternoon Eastern time. ' +
  'Before we confirm, can I verify the service address and the best callback number for you?';

export interface AssessmentResult {
  englishScore: number; // 0-100
  salesScore: number; // 0-100
  typingWpm: number;
  typingAccuracy: number; // 0-100
  compositeScore: number; // 0-100
  tier: 1 | 2 | 3;
}

export function scoreMCQ(questions: MCQuestion[], answers: Record<string, number>): number {
  if (!questions.length) return 0;
  const correct = questions.filter((q) => answers[q.id] === q.correctIndex).length;
  return Math.round((correct / questions.length) * 100);
}

export function typingAccuracy(sample: string, typed: string): number {
  if (!typed.length) return 0;
  const len = Math.min(sample.length, typed.length);
  let hits = 0;
  for (let i = 0; i < len; i += 1) if (sample[i] === typed[i]) hits += 1;
  return Math.round((hits / Math.max(sample.length, typed.length)) * 100);
}

export function typingWpm(typed: string, elapsedSeconds: number): number {
  if (elapsedSeconds <= 0) return 0;
  return Math.round((typed.length / 5) / (elapsedSeconds / 60));
}

export function buildResult(
  englishScore: number,
  salesScore: number,
  wpm: number,
  accuracy: number,
): AssessmentResult {
  const typingScore = Math.min(100, Math.round((Math.min(wpm, 60) / 60) * 60 + (accuracy / 100) * 40));
  const compositeScore = Math.round(englishScore * 0.45 + salesScore * 0.35 + typingScore * 0.2);
  const tier: 1 | 2 | 3 = compositeScore >= 85 ? 3 : compositeScore >= 65 ? 2 : 1;
  return { englishScore, salesScore, typingWpm: wpm, typingAccuracy: accuracy, compositeScore, tier };
}
