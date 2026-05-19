from transformers import pipeline

# Load GPT-2 on CPU
generator = pipeline("text-generation", model="gpt2")

print("GPT-2 CLI (Ctrl+C to quit)")
while True:
    try:
        prompt = input("\n> ")
        if not prompt.strip():
            continue
        output = generator(
            prompt,
            max_new_tokens=50,
            do_sample=True,
            temperature=0.8,
        )
        print("\n" + output[0]["generated_text"])
    except KeyboardInterrupt:
        print("\nBye.")
        break
