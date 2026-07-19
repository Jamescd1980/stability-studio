from studio_edge.intents import classify

cases = [
    'Have Nari send the last image she made over to Orla and have Orla display it.',
    'have Nari sin the last image she made over to Orla and have O er let display it',
    'Have Nari make an image of Fern on the beach',
    'have Orla open the last image',
]
for q in cases:
    i = classify(q)
    print(f"{i.kind:12} | {q[:70]}")
