import Groq from 'groq-sdk';

const groq = new Groq({
  apiKey: process.env.GROQ_API_KEY,
});

const MODEL = 'llama-3.3-70b-versatile';

export interface QuizQuestion {
  question: string;
  options: string[];
  correctAnswer: number;
  explanation: string;
}

export async function generateQuiz(
  content: string,
  numQuestions: number = 10,
  difficulty: string = 'medium'
): Promise<QuizQuestion[]> {
  const prompt = `You are an educational quiz generator. Based on the following study material, generate exactly ${numQuestions} multiple-choice questions at ${difficulty} difficulty level.

IMPORTANT: Return ONLY a valid JSON array, no other text. Each object must have:
- "question": the question text
- "options": array of exactly 4 options
- "correctAnswer": index (0-3) of the correct option
- "explanation": brief explanation of why the answer is correct

Study Material:
${content.slice(0, 12000)}

Return ONLY the JSON array:`;

  const response = await groq.chat.completions.create({
    model: MODEL,
    messages: [{ role: 'user', content: prompt }],
    temperature: 0.7,
    max_tokens: 4000,
    response_format: { type: 'json_object' },
  });

  const text = response.choices[0]?.message?.content || '[]';

  try {
    const parsed = JSON.parse(text);
    // Handle both direct array and wrapped object
    const questions = Array.isArray(parsed) ? parsed : parsed.questions || parsed.quiz || [];
    return questions.slice(0, numQuestions);
  } catch {
    console.error('Failed to parse quiz response:', text);
    throw new Error('Failed to generate quiz. Please try again.');
  }
}

export async function generateSummary(
  content: string
): Promise<{ content: string; keyPoints: string[] }> {
  const prompt = `You are an educational content summarizer. Summarize the following study material in a clear, student-friendly way.

IMPORTANT: Return ONLY a valid JSON object with:
- "content": a comprehensive summary (3-5 paragraphs, use markdown formatting)
- "keyPoints": array of 5-10 key takeaways as short bullet points

Study Material:
${content.slice(0, 15000)}

Return ONLY the JSON object:`;

  const response = await groq.chat.completions.create({
    model: MODEL,
    messages: [{ role: 'user', content: prompt }],
    temperature: 0.5,
    max_tokens: 3000,
    response_format: { type: 'json_object' },
  });

  const text = response.choices[0]?.message?.content || '{}';

  try {
    const parsed = JSON.parse(text);
    return {
      content: parsed.content || parsed.summary || 'No summary generated.',
      keyPoints: parsed.keyPoints || parsed.key_points || [],
    };
  } catch {
    console.error('Failed to parse summary response:', text);
    throw new Error('Failed to generate summary. Please try again.');
  }
}

export async function generateMultiUnitSummary(
  units: Array<{ unitName: string; content: string }>
): Promise<{ content: string; keyPoints: string[] }> {
  const combinedContent = units
    .map(u => `=== ${u.unitName} ===\n${u.content}`)
    .join('\n\n');

  const prompt = `You are an educational content summarizer. Create a comprehensive combined summary of the following study units. Show connections between topics across units.

IMPORTANT: Return ONLY a valid JSON object with:
- "content": a comprehensive combined summary (use markdown with headers for each unit's key topics, then a synthesis section)
- "keyPoints": array of 8-15 key takeaways that span all units

Units covered: ${units.map(u => u.unitName).join(', ')}

Study Material:
${combinedContent.slice(0, 20000)}

Return ONLY the JSON object:`;

  const response = await groq.chat.completions.create({
    model: MODEL,
    messages: [{ role: 'user', content: prompt }],
    temperature: 0.5,
    max_tokens: 4000,
    response_format: { type: 'json_object' },
  });

  const text = response.choices[0]?.message?.content || '{}';

  try {
    const parsed = JSON.parse(text);
    return {
      content: parsed.content || parsed.summary || 'No summary generated.',
      keyPoints: parsed.keyPoints || parsed.key_points || [],
    };
  } catch {
    console.error('Failed to parse multi-unit summary response:', text);
    throw new Error('Failed to generate summary. Please try again.');
  }
}
