import fs from 'fs';
// eslint-disable-next-line @typescript-eslint/no-require-imports
const pdfParse = require('pdf-parse');

export async function extractTextFromFile(filePath: string, fileType: string): Promise<string> {
  if (!fs.existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }

  if (fileType === 'pdf') {
    const buffer = fs.readFileSync(filePath);
    const data = await pdfParse(buffer);
    return data.text;
  }

  // For PPT/DOC files, return a message indicating extraction isn't supported yet
  // In production, you'd use libraries like mammoth (docx) or pptx-parser
  return `[Text extraction for ${fileType} files is not yet supported. Please upload PDF files for AI features.]`;
}

export async function extractTextFromMultipleFiles(
  files: Array<{ filePath: string; fileType: string; title: string }>
): Promise<string> {
  const texts: string[] = [];

  for (const file of files) {
    try {
      const text = await extractTextFromFile(file.filePath, file.fileType);
      if (text && !text.startsWith('[Text extraction')) {
        texts.push(`--- ${file.title} ---\n${text}`);
      }
    } catch (error) {
      console.error(`Failed to extract text from ${file.title}:`, error);
    }
  }

  return texts.join('\n\n');
}
