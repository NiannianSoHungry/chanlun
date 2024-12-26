# -*- coding: utf-8 -*-
"""
Created on Sun Dec  8 16:37:11 2024

@author: Administrator
"""

import baostock as bs
import numpy as np
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import sys
import warnings
warnings.filterwarnings('ignore')

RED_FORMAT = '\033[0;41m{}\033[0m'
GREEN_FORMAT = '\033[0;42m{}\033[0m'

def init():
    CODES = '''
    | 股票名称 | 股票代码  |
    | 上证综指 | sh.000001 |
    | 沪深300  | sh.000300 |
    | 超大盘   | sh.000043 |
    | 中证500  | sh.000905 |
    | 中证100  | sh.000903 |
    | 中小板指 | sz.399005 |
    | 创业板指 | sz.399006 |
    | 300能源  | sh.000908 |
    | 300材料  | sh.000909 |
    | 300工业  | sh.000910 |
    | 300可选  | sh.000911 |
    | 300消费  | sh.000912 |
    | 300医药  | sh.000913 |
    | 300金融  | sh.000914 |
    | 300公用  | sh.000917 |
    '''

    NOW = datetime.datetime.now()
    NOW_STR = NOW.strftime('%Y-%m-%d')

    ADAY = datetime.timedelta(days = 1)



    print("Press 'v' to view codes")
    print("Press 'q' to quit")
    code = input("Code: ")
    code = 'sh.000300' if code == '' else code
    if code == 'q':
        bs.logout()
        sys.exit()
    if code == 'v':
        print(CODES)
        return(code, 0, 0, 0, 0)

    end_date = input('End Date (YY-mm-dd): ')
    end_date = NOW_STR if end_date == '' else end_date
    end_datetime = datetime.datetime.strptime(end_date, '%Y-%m-%d')

    internal = input('Internal (Days): ')
    freq = input('Frequency (d/30/5): ')
    freq = 'd' if freq == '' else freq
    if internal == '':
        if freq == 'd':
            internal = 180
        elif freq == '30':
            internal = 30
        if freq == '5':
            internal = 14
    internal = int(internal)

    if freq == 'd':
        fields = 'date,code,open,high,low,close'
    elif freq == '30' or freq == '5':
        fields = 'time,code,open,high,low,close'

    start_datetime = end_datetime - internal * ADAY
    start_date = start_datetime.strftime('%Y-%m-%d')

    return(code, start_date, end_date, freq, fields)

def get_k(code, start_date, end_date, freq, fields):
    rs = bs.query_history_k_data_plus(
        code = code
        , fields = fields
        , frequency = freq
        , start_date = start_date
        , end_date = end_date
    )
    print('query '+rs.error_msg+'!')

    data_list = []
    if rs.error_code != '0':
        print(RED_FORMAT.format('CANNOT GET DATA'))
        return(None, False)
    else:
        while rs.next():
            data_list.append(rs.get_row_data())

    result = pd.DataFrame(data_list, columns = ['date', 'code', 'open', 'high', 'low', 'close'])
    if freq == '30' or freq == '5':
        result.date = result.date.str[:12]
    result.date = pd.to_datetime(result.date)
    result.open = result.open.astype('float64')
    result.high = result.high.astype('float64')
    result.low = result.low.astype('float64')
    result.close = result.close.astype('float64')

    result = result.reindex(columns = result.columns.tolist() + ['trend', 'color', 'edgecolor', 'order'])
    result.trend = result.open < result.close
    result.loc[result.trend, 'color'] = 'white'
    result.loc[result.trend, 'edgecolor'] = 'red'
    result.loc[~result.trend, 'color'] = 'green'
    result.loc[~result.trend, 'edgecolor'] = 'green'
    result.order = result.index.copy()

    if len(result) < 1:
        print(RED_FORMAT.format('CANNOT GET DATA'))
        return(None, False)
    else:
        return(result, True)

def trend(x, y):
    if y.high >= x.high:
        return 'up'
    elif y.high < x.high:
        return 'down'

def contain(x, y):
    return not ((x.high > y.high) == (x.low > y.low))

def solve(trend, x, y):
    if trend == 'up':
        zhigh = x.high if x.high > y.high else y.high
        zlow = x.low if x.low > y.low else y.low
    elif  trend == 'down':
        zhigh = x.high if x.high < y.high else y.high
        zlow = x.low if x.low < y.low else y.low

    return (zhigh, zlow)

def solve_k(k):
    k_solve = k.iloc[:2]

    if contain(k_solve.iloc[0], k_solve.iloc[1]):
        tr = 'up'
    else:
        tr = trend(k_solve.iloc[0], k_solve.iloc[1])

    x = k_solve.iloc[len(k_solve)-1]
    y = k.iloc[2]
    if contain(x, y):
        zhigh, zlow = solve(tr, x, y)
        tmp = pd.DataFrame({
            'date': [y.date]
            , 'code': [y.code]
            , 'high': [zhigh]
            , 'low': [zlow]
            , 'order': [y.order]
        })
        k_solve = k_solve.iloc[:len(k_solve)-1]
        k_solve = k_solve._append(tmp)
    else:
        k_solve = k_solve._append(y)

    for i in range(3, len(k)):
        tr = trend(k_solve.iloc[len(k_solve)-2], k_solve.iloc[len(k_solve)-1])
        x = k_solve.iloc[len(k_solve)-1]
        y = k.iloc[i]
        if contain(x, y):
            zhigh, zlow = solve(tr, x, y)
            tmp = pd.DataFrame({
                'date': [y.date]
                , 'code': [y.code]
                , 'high': [zhigh]
                , 'low': [zlow]
                , 'order': [y.order]
            })
            k_solve = k_solve.iloc[:len(k_solve)-1]
            k_solve = k_solve._append(tmp, ignore_index = True)
        else:
            k_solve = k_solve._append(y, ignore_index = True)

    for i in range(len(k_solve)):
        if k_solve.iloc[i].open > k_solve.close[i]:
            k_solve.at[i, 'open'] = k_solve.high[i]
            k_solve.at[i, 'close'] = k_solve.low[i]
        else:
            k_solve.at[i, 'open'] = k_solve.low[i]
            k_solve.at[i, 'close'] = k_solve.high[i]

    k_solve.trend = k_solve.open < k_solve.close

    k_solve.loc[k_solve['trend'], 'color'] = 'white'
    k_solve.loc[k_solve['trend'], 'edgecolor'] = 'red'
    k_solve.loc[~k_solve['trend'], 'color'] = 'green'
    k_solve.loc[~k_solve['trend'], 'edgecolor'] = 'green'

    k_solve = k_solve.reindex(columns = k_solve.columns.to_list() + ['order_solve'])
    k_solve.order_solve = k_solve.index.copy()

    return k_solve

def frac(k):
    try:
        fr = pd.DataFrame({
            'date': []
            , 'price': []
            , 'type': []
            , 'order': []
            , 'order_solve': []
        })

        for i in range(1, len(k)-1):
            a = k.iloc[i-1]
            b = k.iloc[i]
            c = k.iloc[i+1]
            if b.high > a.high and b.high > c.high:
                tmp = pd.DataFrame({
                    'date': [b.date]
                    , 'price': [b.high]
                    , 'type': ['top']
                    , 'order': [b.order]
                    , 'order_solve': [b.order_solve]
                })
                fr = fr._append(tmp, ignore_index = True)
            elif b.high < a.high and b.high < c.high:
                tmp = pd.DataFrame({
                    'date': [b.date]
                    , 'price': [b.low]
                    , 'type': ['bottom']
                    , 'order': [b.order]
                    , 'order_solve': [b.order_solve]
                })
                fr = fr._append(tmp, ignore_index = True)

        if len(fr) > 0:
            return fr
        else:
            return None

    except:
        return None

def brush(fr):
    try:
        br = fr.iloc[:1]

        for i in range(1, len(fr)):
            a = br.iloc[len(br)-1]
            b = fr.iloc[i]
            if b.type != a.type and b.order_solve-a.order_solve >= 4:
                if b.type == 'top' and b.price > a.price:
                    br = br._append(b)
                elif b.type == 'bottom' and b.price < a.price:
                    br = br._append(b)
            elif b.type == a.type:
                if b.type == 'top' and b.price > a.price:
                    br = br.iloc[:len(br)-1]
                    br = br._append(b, ignore_index = True)
                elif b.type == 'bottom' and b.price < a.price:
                    br = br.iloc[:len(br)-1]
                    br = br._append(b, ignore_index = True)

        if len(br) > 0:
            return br
        else:
            return None
    except:
        return None

def segment(br):
    try:
        flag = br.price.iloc[1] > br.price.iloc[0]

        if flag:
            if br.price.iloc[3] < br.price.iloc[0]:
                seg = br.iloc[1:2]
                start = 5
                flag = not flag
            else:
                seg = br.iloc[:1]
                start = 4
        else:
            if br.price.iloc[3] > br.price.iloc[0]:
                seg = br.iloc[1:2]
                start = 5
                flag = not flag
            else:
                seg = br.iloc[:1]
                start = 4

        flag2 = False
        for i in range(start, len(br)):
            if flag2:
                flag2 = False
                continue
            if flag:
                if br.type.iloc[i] == 'top':
                    if br.price.iloc[i] < br.price.iloc[i-2]:
                        seg = seg._append(br.iloc[i-2])
                        flag2 = True
                        flag = not flag
            else:
                if br.type.iloc[i] == 'bottom':
                    if br.price.iloc[i] > br.price.iloc[i-2]:
                        seg = seg._append(br.iloc[i-2])
                        flag2 = True
                        flag = not flag

        seg.index = seg.order
        seg = seg.sort_index()

        if len(seg) > 0:
            return seg
        else:
            return None
    except:
        return None

def boll(k):
    try:
        rolling_mean = k.close.rolling(20).mean()
        std = k.close.rolling(20).std(ddof = 0)
        up = rolling_mean + std * 2
        down = rolling_mean - std * 2

        bo = pd.DataFrame({
            'date': k.date
            , 'up': up
            , 'down': down
            , 'order': k.order
        })

        if len(bo) > 0:
            return bo
        else:
            return None
    except:
        return None

def ma_calc(k):
    try:
        ma5 = k.close.rolling(5).mean()
        ma10 = k.close.rolling(10).mean()

        ma = pd.DataFrame({
            'date': k.date
            , 'ma5': ma5
            , 'ma10':  ma10
            , 'order': k.order
        })

        if len(ma) > 0:
            return ma
        else:
            return None
    except:
        return None

def macd_calc(k):
    try:
        ema1 = k.close.ewm(span = 12, adjust = False).mean()
        ema2 = k.close.ewm(span = 26, adjust = False).mean()
        dif = ema1 - ema2
        dea = dif.copy()
        for i in range(1, len(dea)):
            dea.iloc[i] = dea.iloc[i-1]*0.8 + dea.iloc[i]*0.2
        delta = (dif - dea) * 2
        color = delta.copy()
        color.loc[delta >= 0] = 'red'
        color.loc[delta < 0] = 'green'
        macd = pd.DataFrame({
            'date': k.date
            , 'dif': dif
            , 'dea': dea
            , 'delta': delta
            , 'color': color
            , 'order': k.order
        })

        if len(macd) > 0:
            return macd
        else:
            return None
    except:
        return None

def plot_k(code, k, order, freq, br = None, seg = None, tr = None, bo = None, macd = None, ma = None):
    if freq == 'd':
        xticks = k[order].loc[k.date.dt.day_name() == 'Monday']
        fmt = '%Y-%m-%d'
    elif freq == '30' or freq == '5':
        xticks = k[order].loc[k.date.hour == 0]
        fmt = '%Y-%m-%d %H:%m'

    if len(xticks) < 30:
        xticks = k[order]
    if len(xticks) > 30:
        xticks = xticks.iloc[
            np.arange(
                0
                , len(xticks)
                , np.ceil(len(xticks)/30)
            )
        ]

    xticklabels = k.date.loc[k[order].isin(xticks)].dt.strftime(fmt)

    if macd is not None and order == 'order':
        fig, (ax1, ax2) = plt.subplots(2, 1, height_ratios = (3, 1))
        ax2.bar(
            x = macd[order]
            , height = macd.delta
            , color = macd.color
            , bottom = 0
            , linewidth = 1
            , zorder = 1
        )
        ax2.plot(
            macd[order]
            , macd.dif
            , color = 'orange'
            , linewidth = 1
            , zorder = 2
        )
        ax2.plot(
            macd[order]
            , macd.dea
            , color = 'blue'
            , linewidth = 1
            , zorder = 3
        )
        ax2.grid(
            True
            , linewidth = 1
            , linestyle = 'dashed'
        )

        ax2.set_xticks(xticks)
        ax2.set_xticklabels(xticklabels)
    else:
        fig, ax1 = plt.subplots()

    plt.subplots_adjust(hspace = 0)
    ax1.grid(
        True
        , linewidth = 1
        , linestyle = 'dashed'
    )
    ax1.vlines(
        x = k[order]
        , ymin = k.low
        , ymax = k.high
        , color = k.edgecolor
        , linewidth = 1
        , zorder = 2
    )
    ax1.bar(
        x = k[order]
        , height = (k.open - k.close)
        , bottom = k.close
        , color = k.color
        , linewidth = 1
        , edgecolor = k.edgecolor
        , zorder = 3
    )

    if ma is not None:
        ax1.plot(
            ma[order]
            , ma.ma5
            , color = 'red'
            , linewidth = 1
            , zorder = 4
        )
        ax1.plot(
            ma[order]
            , ma.ma10
            , color = 'orange'
            , linewidth = 1
            , zorder = 5
        )

    if br is not None:
        ax1.plot(
            br[order]
            , br.price
            , color = 'black'
            , linewidth = 1
            , zorder = 6
        )

    if seg is not None:
        ax1.plot(
            seg[order]
            , seg.price
            , color = 'blue'
            , linewidth = 1
            ,  zorder = 7
        )

    if tr is not None:
        ax1.plot(
            tr[order]
            , tr.price
            , color = 'red'
            , linewidth = 1
            ,  zorder = 8
        )

    if bo is not None:
        ax1.fill_between(
            bo[order]
            , bo.up
            , bo.down
            , color = 'lightgrey'
            , edgecolor = 'black'
            , linestyle = 'dashed'
            , linewidth = 1
            , alpha = 0.6
            , zorder = 1
        )


    title = bs.query_stock_basic(code = code).get_row_data()[1]
    ax1.set_title(
        title
        , fontdict = {
            'family': 'SimHei'
            , 'size': 16
        }
    )
    ax1.set_xticks(xticks)
    ax1.set_xticklabels(xticklabels)

    fig.autofmt_xdate()
    fig.set_figwidth(20)
    fig.set_figheight(12)
    plt.show()

def Kelly_k(k):
    rate = 0
    p = len(k.trend.loc[k.trend])/len(k.trend)
    q = 1-p

    b = (k.close.loc[k.trend] - k.open.loc[k.trend])/k.open.loc[k.trend]
    b = np.exp(np.log(b).mean())

    if np.isnan(b):
        rate = -np.inf
        return rate

    a = (k.open.loc[~k.trend] - k.close.loc[~k.trend])/k.open.loc[~k.trend]
    a = np.exp(np.log(a).mean())

    if np.isnan(a):
        rate = np.inf
        return rate

    rate = p/a - q/b

    return rate

# def Kelly_br(br):
#     rate = 0
#     p = []
#     b = []
#     a = []
#     for i in range(1, len(br)):
#         if br.price.iloc[i] > br.price.iloc[i-1]:
#             p.append(br.order.iloc[i] - br.order.iloc[i-1])
#             b.append(
#                 (br.price.iloc[i] - br.price.iloc[i-1]) / br.price.iloc[i-1]
#             )
#         else:
#             a.append(
#                 (br.price.iloc[i-1] - br.price.iloc[i]) / br.price.iloc[i-1]
#             )

#     p = pd.Series(p).sum() / (br.order.iloc[len(br)-1] - br.order.iloc[0])
#     q = 1-p
#     b = np.exp(np.log(b).mean())
#     a = np.exp(np.log(a).mean())

#     if np.isnan(b):
#         rate = -np.inf
#         return rate
#     if np.isnan(a):
#         rate = np.inf
#         return rate

#     rate = p/a - q/b

#     return rate

if __name__ == '__main__':
    lg = bs.login()
    while True:



        code, start_date, end_date, freq, fields = init()
        if code == 'v':
            continue

        k_raw, flag = get_k(code, start_date, end_date, freq, fields)
        if not flag:
            continue

        k_solve = solve_k(k_raw)
        fr = frac(k_solve)
        br = brush(fr)
        seg = segment(br)
        tr = segment(seg)
        bo = boll(k_raw)
        ma = ma_calc(k_raw)
        macd = macd_calc(k_raw)
        plot_k(
            code = code
            , k = k_raw
            , order = 'order'
            , freq = freq
            , br = br
            , seg = seg
            , tr = tr
            , bo = bo
            , ma = ma
            , macd = macd
        )

        rate = Kelly_k(k_raw)
        rate = 'Hold Position Rate (K): {:.2f}%'.format(rate)
        print(GREEN_FORMAT.format(rate))

