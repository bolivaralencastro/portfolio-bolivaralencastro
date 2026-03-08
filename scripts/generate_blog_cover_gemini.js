#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

function parseArgs(argv) {
  const options = {
    model: "gemini-3-pro-image-preview",
    aspectRatio: undefined,
    imageSize: undefined,
    reference: undefined,
  };
  const positional = [];

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    if (arg === "--model") {
      options.model = argv[index + 1];
      index += 1;
      continue;
    }

    if (arg === "--aspect-ratio") {
      options.aspectRatio = argv[index + 1];
      index += 1;
      continue;
    }

    if (arg === "--image-size") {
      options.imageSize = argv[index + 1];
      index += 1;
      continue;
    }

    if (arg === "--reference") {
      options.reference = argv[index + 1];
      index += 1;
      continue;
    }

    positional.push(arg);
  }

  return { options, positional };
}

function mimeTypeFor(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".png") {
    return "image/png";
  }
  if (ext === ".jpg" || ext === ".jpeg") {
    return "image/jpeg";
  }
  if (ext === ".webp") {
    return "image/webp";
  }
  throw new Error(`Formato de imagem de referencia nao suportado: ${ext}`);
}

async function main() {
  const { options, positional } = parseArgs(process.argv.slice(2));
  const [outputFileArg, ...promptParts] = positional;
  const apiKey = process.env.GEMINI_API_KEY;

  if (!apiKey) {
    throw new Error("Defina GEMINI_API_KEY no ambiente.");
  }

  if (!outputFileArg) {
    throw new Error(
      "Uso: node scripts/generate_blog_cover_gemini.js [--model <model>] [--aspect-ratio <ratio>] [--image-size <size>] [--reference <image>] <output-file> <prompt>"
    );
  }

  const prompt = promptParts.join(" ").trim();
  if (!prompt) {
    throw new Error("Informe um prompt para gerar a imagem.");
  }

  const outputFile = path.resolve(outputFileArg);
  fs.mkdirSync(path.dirname(outputFile), { recursive: true });
  const imageConfig = {};

  if (options.aspectRatio) {
    imageConfig.aspectRatio = options.aspectRatio;
  }

  if (options.imageSize) {
    imageConfig.imageSize = options.imageSize;
  }

  const parts = [{ text: prompt }];
  if (options.reference) {
    const referenceFile = path.resolve(options.reference);
    const referenceBuffer = fs.readFileSync(referenceFile);
    parts.push({
      inline_data: {
        mime_type: mimeTypeFor(referenceFile),
        data: referenceBuffer.toString("base64"),
      },
    });
  }

  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${options.model}:generateContent`,
    {
      method: "POST",
      headers: {
        "x-goog-api-key": apiKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        contents: [
          {
            parts,
          },
        ],
        generationConfig: {
          responseModalities: ["IMAGE"],
          ...(Object.keys(imageConfig).length > 0 ? { imageConfig } : {}),
        },
      }),
    }
  );

  if (!response.ok) {
    throw new Error(`Gemini API ${response.status}: ${await response.text()}`);
  }

  const data = await response.json();
  const imagePart = data.candidates
    ?.flatMap((candidate) => candidate.content?.parts || [])
    .find((part) => part.inlineData?.data);

  if (!imagePart?.inlineData?.data) {
    throw new Error(`Resposta sem imagem: ${JSON.stringify(data)}`);
  }

  const buffer = Buffer.from(imagePart.inlineData.data, "base64");
  fs.writeFileSync(outputFile, buffer);
  console.log(`Imagem salva em ${outputFile}`);
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
