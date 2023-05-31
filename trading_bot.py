from luno_python.client import Client
from time import sleep, time
import numpy as np
import _thread
from tkinter import *

# Setup your account details

key_id = "kuq3ngczrd756"
key_secret = "4MlHhaNBigTevC1SrR8KkMVXK7iu1q0e07QB5697eFo"

# Creates a new client

c = Client(api_key_id=key_id, api_key_secret=key_secret)

# These parameters setup the behaviour

shrt_ma = 12    # The short moving average period
long_ma = 26    # The long moving average period
rsi_lookback_period = 14    # Look back period for calculating RSI
sleep_period = 56 * 5   # Time between candles in seconds
trade_timer_sec = 15    # Timeout period for a trade to execute
trade_diff = 0   # The difference between the current price and what you want to buy/sell at
trade_attempts_val = 5  # How many attempts executing a failed trade until we give up

# Internal global variables

order_pending = False
signal_ema = None
in_position = False
buy_price, sell_price = 0, 0
macd_list = np.array([])
price_history = np.array([])
trade_attempts = trade_attempts_val


# This is where the strategy is implemented
def main():
    global in_position, macd_list, order_pending, price_history

    # Load in the previously captured data to begin trading faster
    load_data()

    # More internal variables
    rsi = 0
    s_ema_yest = None
    l_ema_yest = None
    ema_200_yest = None
    signal = 0

    # The main loop takes place in here
    while True:
        # This <try> prevents any unhandled errors from crashing the program
        try:

            # Get the ticker data and add it to the price_history list
            current_price, res = get_price()
            price_history = np.append(price_history, current_price)

            # Calculate the EMAs and MACD and add it to a list
            ma_a = get_ema(shrt_ma, price_history, s_ema_yest)
            ma_b = get_ema(long_ma, price_history, l_ema_yest)
            ema_200 = get_ema(200, price_history, ema_200_yest)

            macd = get_macd(ma_a, ma_b)
            macd_list = np.append(macd_list, macd)

            # This <try> handles the price_histroy.shape out of range case
            try:
                if macd_list.shape[0] < 9:
                    raise Exception("Not enough data yet")

                # Calculate RSI and the signal line used in MACD - RSI is not used but calculated for future use
                rsi = get_rsi(rsi_lookback_period, price_history)
                signal = get_signal()

                # Decide whether to buy sell or hold
                if not in_position and not order_pending:
                    if signal < macd < 0 and current_price > ema_200:
                        buy(float(res["bid"]) - trade_diff)
                elif in_position and not order_pending:
                    if macd < signal:
                        sell(float(res["ask"]) + trade_diff)
            except Exception as e:
                print(e)

            # Setup variabls for the next cycle
            s_ema_yest = ma_a
            l_ema_yest = ma_b

            # Get the account balances to be recorded into data
            xbt, zar = get_balances()

            # Print out the data - TODO: Put this into its own function
            print("XBT: " + str(xbt) + " ZAR: " + str(zar))
            print(f"RSI: {rsi}, MACD: {macd}, Signal: {signal}")
            print(in_position)
            print(ema_200)

            # Stores out the data to a CSV - TODO: Add this the to store_data function
            data1 = [f"BTC: {xbt}", f"ZAR: {zar}"]
            data2 = [f"Price: {round(current_price)}", f"RSI: {round(rsi)}", f"{shrt_ma}_MA: {round(ma_a)}", f"{long_ma}_MA: {round(ma_b)}"]
            data3 = [f"MACD: {macd}", f"Signal: {signal}"]
            data = [data1, data2, data3]
            store_data(data)

            # Sleeps until next price to be read
            sleep(sleep_period)

        except Exception as e:
            print(e)
##############################################
##############################################


def get_price(price_type='None'):
    res = c.get_ticker(pair='XBTZAR')
    if 'ask' in price_type:
        return int(float(res["ask"]))
    elif 'bid' in price_type:
        return int(float(res["bid"]))
    elif 'avg' in price_type:
        return (int(float(res["ask"])) + int(float(res["bid"]))) / 2
    else:
        return (int(float(res["ask"])) + int(float(res["bid"]))) / 2, res
##############################################
##############################################


# Get the account balances

def get_balances():
    balances = c.get_balances(assets=["ZAR", "XBT"])
    xbt = balances["balance"][0]["balance"]
    zar = balances["balance"][2]["balance"]
    return xbt, zar
##############################################
##############################################


# This funtion keeps track of the current trades status until the trade is executed
# This funtion runs in a seperate thread to avoid blocking of the price collection

def begin_trade_timer(timer_sec, order_id, trade_price):
    global in_position, buy_price, sell_price, order_pending, trade_attempts_val, trade_attempts

    print("Started trade timer")
    order_complete = False
    order_pending = True
    timer_start = int(round(time() * 1000))
    timer = 0
    while not order_complete:
        ords = c.list_orders(state='PENDING')
        try:
            for order in ords['orders']:
                if order_id in order.values():
                    print("Order pending...")
                    if timer > timer_sec * 1000:
                        try:
                            order_pending = True
                            c.stop_order(str(order_id))
                        except:
                            print("Failed to cancel order")
                        print("Order timed out - Trying again")
                        order_pending = False
                        if trade_attempts > 0:
                            trade_attempts -= 1
                            if in_position:
                                sell(get_price('ask') + trade_diff)
                            else:
                                buy(get_price('bid') - trade_diff)
                        else:
                            trade_attempts = trade_attempts_val
                        return
                else:
                    raise Exception
        except:
            order_complete = True
            print("ended trade timer")
        timer = int(round(time() * 1000)) - timer_start
    in_position = not in_position
    order_pending = False
    trade_attempts = trade_attempts_val
    if in_position:
        print("Bought at " + str(trade_price))
    else:
        print("Sold at " + str(trade_price))
##############################################
##############################################


# Gets the simple moving average over n period

def get_ma(n, price_hist):
    try:
        return np.average(price_hist[-n:])
    except Exception as e:
        print(e)
##############################################
##############################################


# Gets the exponential moving average over n period

def get_ema(n, price_hist, ema_yest):
    if ema_yest is None:
        try:
            ema_yest = get_ma(n, price_hist)
        except Exception as e:
            print(e)
    k = 2/(1+n)
    return price_hist[-1:][0] * k + ema_yest * (1 - k)
##############################################
##############################################


# Gets the RSI over n period

def get_rsi(n, price_hist):
    r = price_hist.shape

    if r[0] > (n + 1):
        price_hist = price_hist[-(n+1):]
        avg_gain = avg_loss = avg_gain_count = avg_loss_count = 0

        for i in range(1, n):
            if price_hist[i] > price_hist[i-1]:
                avg_gain += price_hist[i] - price_hist[i-1]
                avg_gain_count += 1
            elif price_hist[i] < price_hist[i-1]:
                avg_loss += abs(price_hist[i] - price_hist[i-1])
                avg_loss_count += 1

        avg_gain = avg_gain / avg_gain_count
        avg_loss = avg_loss / avg_loss_count
        try:
            rsi = 100 - (100/(1+(avg_gain/avg_loss)))
        except ZeroDivisionError:
            return 100
        return rsi
    else:
        print(Exception("Not enough data for RSI calc"))
##############################################
##############################################


# Gets the signal line for the MACD calculation

def get_signal():
    global signal_ema, macd_list
    signal = get_ema(9, macd_list, signal_ema)
    signal_ema = signal

    return signal
##############################################
##############################################


# Gets the MACD indicator value

def get_macd(ma_1, ma_2):
    return ma_1 - ma_2
##############################################
##############################################


# Places a buy order and calls begin_trade_timer in a seperate thread

def buy(price):
    global buy_price, trade_timer_sec
    try:
        c.post_limit_order(pair="XBTZAR", price=price, type="BID",
                           volume=0.001, post_only=True)
    except:
        print("Buy order not executed")
        price = get_price('bid')
        buy(price)
    ord_id = c.list_orders()['orders'][0]['order_id']
    buy_price = price
    try:
        print("here")
        _thread.start_new_thread(begin_trade_timer, (trade_timer_sec, ord_id, buy_price,))
    except:
        print("Unable to start thread")
    return 1
##############################################
##############################################


# Places a sell order and calls begin_trade_timer in a seperate thread

def sell(price):
    global sell_price, trade_timer_sec
    try:
        c.post_limit_order(pair="XBTZAR", price=price + trade_diff, type="ASK",
                           volume=0.001, post_only=True)
    except:
        print("Sell order not executed")
        price = get_price('ask')
        sell(price)
    ord_id = c.list_orders()['orders'][0]['order_id']
    sell_price = price
    try:
        _thread.start_new_thread(begin_trade_timer, (trade_timer_sec, ord_id, sell_price,))
    except:
        print("Unable to start thread")
    return 1
##############################################
##############################################


# Stores the collected data into a CSV file

def store_data(data):
    file = open('trade_bot.csv', mode='a')
    for row in data:
        for item in row:
            file.write(item + '\n')
    file.write("\n")
    file.close()
##############################################
##############################################


# Gets stored data to begin trading

def load_data():
    global price_history, macd_list
    file = open('trade_bot.csv', mode='r')
    for line in file:
        if line == '\n':
            continue
        line = line.replace('\n', '')
        line = line.split(' ')

        if 'Price' in line[0]:
            price_history = np.append(price_history, float(line[1]))
        elif 'MACD' in line[0]:
            macd_list = np.append(macd_list, float(line[1]))
##############################################
##############################################


def set_rsi_lookback(args):
    global rsi_lookback_period
    rsi_lookback_period = 50
##############################################
##############################################


def begin_gui():
    top = Tk()
    w = Entry(top, bd=5)
    w.bind('<Return>', set_rsi_lookback)
    w.pack(side=RIGHT)
    _thread.start_new_thread(top.mainloop(), ())
##############################################
##############################################


def set_sma():
    pass
##############################################
##############################################


def set_lma():
    pass
##############################################
##############################################


def set_sleep_period():
    pass
##############################################
##############################################


def set_trade_timer():
    pass
##############################################
##############################################


def set_trade_attempts():
    pass
##############################################
##############################################


if __name__ == "__main__":
    main()
