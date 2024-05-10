import hashlib
import codecs

input_file = open('input.txt', 'rb')
input_text = codecs.decode(input_file.read())

obj_sha3_256 = hashlib.sha3_256(input_text.encode())

print("\nSHA3-256 Hash: ", obj_sha3_256.hexdigest())