import pickle

try:
    with open('EncodeFile.p', 'rb') as file:
        encodeListKnowWithIds = pickle.load(file)
        encodeListKnow, UserId = encodeListKnowWithIds
        print('User IDs in EncodeFile:', UserId)
        print('\nNumber of encoded faces:', len(encodeListKnow))
        print('Number of user IDs:', len(UserId))
except FileNotFoundError:
    print('EncodeFile.p not found')
except Exception as e:
    print('Error reading EncodeFile.p:', str(e)) 