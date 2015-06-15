# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from Peach.transformer import Transformer


# Initial permutation
IP = (
    58, 50, 42, 34, 26, 18, 10, 2,
    60, 52, 44, 36, 28, 20, 12, 4,
    62, 54, 46, 38, 30, 22, 14, 6,
    64, 56, 48, 40, 32, 24, 16, 8,
    57, 49, 41, 33, 25, 17,  9, 1,
    59, 51, 43, 35, 27, 19, 11, 3,
    61, 53, 45, 37, 29, 21, 13, 5,
    63, 55, 47, 39, 31, 23, 15, 7,
)

# Final permutation, FP = IP^(-1)
FP = (
    40, 8, 48, 16, 56, 24, 64, 32,
    39, 7, 47, 15, 55, 23, 63, 31,
    38, 6, 46, 14, 54, 22, 62, 30,
    37, 5, 45, 13, 53, 21, 61, 29,
    36, 4, 44, 12, 52, 20, 60, 28,
    35, 3, 43, 11, 51, 19, 59, 27,
    34, 2, 42, 10, 50, 18, 58, 26,
    33, 1, 41,  9, 49, 17, 57, 25,
)

# Permuted-choice 1 from the key bits to yield C and D.
# Note that bits 8,16... are left out: They are intended for a parity check.
PC1_C = (
    57, 49, 41, 33, 25, 17,  9,
    1, 58, 50, 42, 34, 26, 18,
    10,  2, 59, 51, 43, 35, 27,
    19, 11,  3, 60, 52, 44, 36,
)
PC1_D = (
    63, 55, 47, 39, 31, 23, 15,
     7, 62, 54, 46, 38, 30, 22,
    14,  6, 61, 53, 45, 37, 29,
    21, 13,  5, 28, 20, 12,  4,
)

# Permuted-choice 2, to pick out the bits from the CD array that generate the
# key schedule.
PC2_C = (
    14, 17, 11, 24,  1,  5,
     3, 28, 15,  6, 21, 10,
    23, 19, 12,  4, 26,  8,
    16,  7, 27, 20, 13,  2,
)
PC2_D = (
    41, 52, 31, 37, 47, 55,
    30, 40, 51, 45, 33, 48,
    44, 49, 39, 56, 34, 53,
    46, 42, 50, 36, 29, 32,
)

# The C and D arrays are used to calculate the key schedule.
C = [0] * 28
D = [0] * 28

# The key schedule. Generated from the key.
KS = [[0] * 48 for _ in range(16)]

# The E bit-selection table.
E = [0] * 48
e2 = (
    32,  1,  2,  3,  4,  5,
     4,  5,  6,  7,  8,  9,
     8,  9, 10, 11, 12, 13,
    12, 13, 14, 15, 16, 17,
    16, 17, 18, 19, 20, 21,
    20, 21, 22, 23, 24, 25,
    24, 25, 26, 27, 28, 29,
    28, 29, 30, 31, 32,  1,
)

# S-boxes.
S = (
    (
        14,  4, 13,  1,  2, 15, 11,  8,  3, 10,  6, 12,  5,  9,  0,  7,
         0, 15,  7,  4, 14,  2, 13,  1, 10,  6, 12, 11,  9,  5,  3,  8,
         4,  1, 14,  8, 13,  6,  2, 11, 15, 12,  9,  7,  3, 10,  5,  0,
        15, 12,  8,  2,  4,  9,  1,  7,  5, 11,  3, 14, 10,  0,  6, 13
    ),
    (
        15,  1,  8, 14,  6, 11,  3,  4,  9,  7,  2, 13, 12,  0,  5, 10,
         3, 13,  4,  7, 15,  2,  8, 14, 12,  0,  1, 10,  6,  9, 11,  5,
         0, 14,  7, 11, 10,  4, 13,  1,  5,  8, 12,  6,  9,  3,  2, 15,
        13,  8, 10,  1,  3, 15,  4,  2, 11,  6,  7, 12,  0,  5, 14,  9
    ),
    (
        10,  0,  9, 14,  6,  3, 15,  5,  1, 13, 12,  7, 11,  4,  2,  8,
        13,  7,  0,  9,  3,  4,  6, 10,  2,  8,  5, 14, 12, 11, 15,  1,
        13,  6,  4,  9,  8, 15,  3,  0, 11,  1,  2, 12,  5, 10, 14,  7,
         1, 10, 13,  0,  6,  9,  8,  7,  4, 15, 14,  3, 11,  5,  2, 12
    ),
    (
         7, 13, 14,  3,  0,  6,  9, 10,  1,  2,  8,  5, 11, 12,  4, 15,
        13,  8, 11,  5,  6, 15,  0,  3,  4,  7,  2, 12,  1, 10, 14,  9,
        10,  6,  9,  0, 12, 11,  7, 13, 15,  1,  3, 14,  5,  2,  8,  4,
         3, 15,  0,  6, 10,  1, 13,  8,  9,  4,  5, 11, 12,  7,  2, 14
    ),
    (
         2, 12,  4,  1,  7, 10, 11,  6,  8,  5,  3, 15, 13,  0, 14,  9,
        14, 11,  2, 12,  4,  7, 13,  1,  5,  0, 15, 10,  3,  9,  8,  6,
         4,  2,  1, 11, 10, 13,  7,  8, 15,  9, 12,  5,  6,  3,  0, 14,
        11,  8, 12,  7,  1, 14,  2, 13,  6, 15,  0,  9, 10,  4,  5,  3
    ),
    (
        12,  1, 10, 15,  9,  2,  6,  8,  0, 13,  3,  4, 14,  7,  5, 11,
        10, 15,  4,  2,  7, 12,  9,  5,  6,  1, 13, 14,  0, 11,  3,  8,
         9, 14, 15,  5,  2,  8, 12,  3,  7,  0,  4, 10,  1, 13, 11,  6,
         4,  3,  2, 12,  9,  5, 15, 10, 11, 14,  1,  7,  6,  0,  8, 13
    ),
    (
         4, 11,  2, 14, 15,  0,  8, 13,  3, 12,  9,  7,  5, 10,  6,  1,
        13,  0, 11,  7,  4,  9,  1, 10, 14,  3,  5, 12,  2, 15,  8,  6,
         1,  4, 11, 13, 12,  3,  7, 14, 10, 15,  6,  8,  0,  5,  9,  2,
         6, 11, 13,  8,  1,  4, 10,  7,  9,  5,  0, 15, 14,  2,  3, 12
    ),
    (
        13,  2,  8,  4,  6, 15, 11,  1, 10,  9,  3, 14,  5,  0, 12,  7,
         1, 15, 13,  8, 10,  3,  7,  4, 12,  5,  6, 11,  0, 14,  9,  2,
         7, 11,  4,  1,  9, 12, 14,  2,  0,  6, 10, 13, 15,  3,  5,  8,
         2,  1, 14,  7,  4, 10,  8, 13, 15, 12,  9,  0,  3,  5,  6, 11
    )
)

# P is a permutation on the selected combination of the current L and key.
P = (
    16,  7, 20, 21,
    29, 12, 28, 17,
     1, 15, 23, 26,
     5, 18, 31, 10,
     2,  8, 24, 14,
    32, 27,  3,  9,
    19, 13, 30,  6,
    22, 11,  4, 25,
)

# The combination of the key and the input, before selection.
preS = [0] * 48


def __setkey(key):
    """Set up the key schedule from the encryption key."""
    global C, D, KS, E

    shifts = (1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1)

    # First, generate C and D by permuting the key. The lower order bit of each
    # 8-bit char is not used, so C and D are only 28 bits apiece.
    for i in range(28):
        C[i] = key[PC1_C[i] - 1]
        D[i] = key[PC1_D[i] - 1]

    for i in range(16):
        # rotate
        for k in range(shifts[i]):
            temp = C[0]

            for j in range(27):
                C[j] = C[j + 1]

            C[27] = temp
            temp = D[0]
            for j in range(27):
                D[j] = D[j + 1]

            D[27] = temp

        # get Ki. Note C and D are concatenated
        for j in range(24):
            KS[i][j] = C[PC2_C[j] - 1]
            KS[i][j + 24] = D[PC2_D[j] - 28 - 1]

    # load E with the initial E bit selections
    for i in range(48):
        E[i] = e2[i]


def __encrypt(block):
    global preS

    left, right = [], []  # block in two halves
    f = [0] * 32

    # First, permute the bits in the input
    for j in range(32):
        left.append(block[IP[j] - 1])

    for j in range(32, 64):
        right.append(block[IP[j] - 1])

    # Perform an encryption operation 16 times.
    for i in range(16):
        # Save the right array, which will be the new left.
        old = right[:]

        # Expand right to 48 bits using the E selector and exclusive-or with
        # the current key bits.
        for j in range(48):
            preS[j] = right[E[j] - 1] ^ KS[i][j]

        # The pre-select bits are now considered in 8 groups of 6 bits each.
        # The 8 selection functions map these 6-bit quantities into 4-bit
        # quantities and the results are permuted to make an f(R, K).
        # The indexing into the selection functions is peculiar; it could be
        # simplified by rewriting the tables.
        for j in range(8):
            temp = 6 * j
            k = S[j][(preS[temp + 0] << 5) +
                     (preS[temp + 1] << 3) +
                     (preS[temp + 2] << 2) +
                     (preS[temp + 3] << 1) +
                     (preS[temp + 4] << 0) +
                     (preS[temp + 5] << 4)]

            temp = 4 * j
            f[temp + 0] = (k >> 3) & 1
            f[temp + 1] = (k >> 2) & 1
            f[temp + 2] = (k >> 1) & 1
            f[temp + 3] = (k >> 0) & 1

        # The new right is left ^ f(R, K).
        # The f here has to be permuted first, though.
        for j in range(32):
            right[j] = left[j] ^ f[P[j] - 1]

        # Finally the new left (the original right) is copied back.
        left = old

    # The output left and right are reversed.
    left, right = right, left

    # The final output gets the inverse permutation of the very original
    for j in range(64):
        i = FP[j]
        if i < 33:
            block[j] = left[i - 1]
        else:
            block[j] = right[i - 33]

    return block


def crypt(pw, salt):
    iobuf = []

    # break pw into 64 bits
    block = []
    for c in pw:
        c = ord(c)
        for j in range(7):
            block.append((c >> (6 - j)) & 1)
        block.append(0)
    block += [0] * (64 - len(block))

    # set key based on pw
    __setkey(block)

    for i in range(2):
        # store salt at beginning of results
        iobuf.append(salt[i])
        c = ord(salt[i])

        if c > ord('Z'):
            c -= 6

        if c > ord('9'):
            c -= 7

        c -= ord('.')

        # use salt to effect the E-bit selection
        for j in range(6):
            if (c >> j) & 1:
                E[6 * i + j], E[6 * i + j + 24] = E[6 * i + j + 24], E[6 * i + j]

    # call DES encryption 25 times using pw as key and initial data = 0
    block = [0] * 66
    for i in range(25):
        block = __encrypt(block)

    # format encrypted block for standard crypt(3) output
    for i in range(11):
        c = 0
        for j in range(6):
            c <<= 1
            c |= block[6 * i + j]

        c += ord('.')
        if c > ord('9'):
            c += 7

        if c > ord('Z'):
            c += 6

        iobuf.append(chr(c))

    return ''.join(iobuf)


class Crypt(Transformer):
    """UNIX style crypt.
    If no salt is specified will use first two chars of data, ala pwd style.
    """

    _salt = None

    def __init__(self, salt=None):
        """
        :param salt: salt for crypt (optional)
        :type salt: str
        """
        Transformer.__init__(self)
        self._salt = salt

    def realEncode(self, data):
        if self._salt is None:
            return crypt(data, data[:2])
        return crypt(data, self._salt)