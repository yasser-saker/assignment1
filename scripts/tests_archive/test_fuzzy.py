from rapidfuzz import fuzz

expected = "PNT-01 (9'-0\" High):\n-Mfg: Sherwin Williams\n-Color: Wordly Gray #SW7043\n-Type: Eggshell"
predicted = "PNT-01 (9'-0\" High):\n-Mfg: Sherwin Williams\n-Color: Wordly Gray #SW7043\n-Type: Eggshell"

score = fuzz.ratio(expected.lower(), predicted.lower())
print('Score:', score)
print()
print('Expected repr:', repr(expected))
print('Predicted repr:', repr(predicted))
