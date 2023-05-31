from trading_bot import shrt_ma, long_ma
import matplotlib.pyplot as plt

rng = 200

BTC = []
ZAR = []
RSI = []
S_MA = []
L_MA = []
Ord_suc = []
In_pos = []
file = open('trade_bot2.csv', 'r')

for line in file:
    if line == '\n':
        continue
    # line = line.replace('\n', '')
    line = line.split(' ')

    print(line)

    if 'BTC' in line[0]:
        BTC.append(line[1])
    elif 'ZAR' in line[0]:
        ZAR.append(line[1])
    elif 'RSI' in line[0]:
        RSI.append(int(float(line[1])))
    elif f"{shrt_ma}_MA" in line[0]:
        S_MA.append(int(float(line[1])))
    elif f"{long_ma}_MA" in line[0]:
        L_MA.append(int(float(line[1])))
    elif 'Order_success' in line[0]:
        Ord_suc.append(line[1])
    elif 'In_position' in line[0]:
        In_pos.append(line[1])

# fig = plt.figure()
# ax1 = plt.axes([0.1, 0.01, 0.5, 0.5])
# ax2 = plt.axes([0.1, 0.5, 0.5, 0.4])
#
# indexes = [i for i in range(len(RSI[-rng:]))]
# ax1.plot(indexes, RSI[-rng:])
#
# ax2.plot(indexes, S_MA[-rng:], indexes, L_MA[-rng:])
#
# plt.show()