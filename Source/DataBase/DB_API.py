
import os, datetime, configparser
import pandas as pd
from bson import json_util

global_config = None
global_client = None

def getConfig(root_path):
    global global_config
    if global_config is None:
        print("initial Config...")
        global_config = configparser.ConfigParser()
        global_config.read(root_path + "/" + "config.ini")
    return global_config

def getClient():
    global global_client
    from pymongo import MongoClient
    if global_client is None: 
        print("initial DB Client...")
        global_client = MongoClient('localhost', 27017)
    return global_client

def getCollection(database, collection):
    client = getClient()
    db = client[database]
    return db[collection]

def readFromCollection(collection, queryString):
    if len(queryString) == 0: return pd.DataFrame(list(collection.find()))
    return pd.DataFrame(list(collection.find(queryString)))

def writeToCollection(collection, df):
    jsonStrings = df.to_json(orient='records')
    bsonStrings = json_util.loads(jsonStrings)
    collection.insert_many(bsonStrings, ordered=False)

def writeToCSV(csv_dir, CollectionKey, df):
    if os.path.exists(csv_dir) == False:
        os.makedirs(csv_dir)
    filename = csv_dir + CollectionKey + '.csv'
    df.to_csv(filename)


def queryStockList(root_path, database):
    #symbol_exception = ['AXON', 'CTT', 'ARL']
    CollectionKey = "StockList"
    config = getConfig(root_path)
    storeType = int(config.get('Setting', 'StoreType'))
    
    try:
        if storeType == 1:
            collection = getCollection(database, CollectionKey)
            return readFromCollection(collection, {})
            
        if storeType == 2:
            csv_dir = root_path + "/" + config.get('Paths', database) + config.get('Paths', 'STOCK_SHARE')
            filename = csv_dir + CollectionKey + '.csv'
            return pd.read_csv(filename, index_col=0)

    except Exception as e:
        print("queryStockList Exception", e)
        return pd.DataFrame()
    
    return pd.DataFrame()

def storeStockList(root_path, database, df):
    CollectionKey = "StockList"
    config = getConfig(root_path)
    storeType = int(config.get('Setting', 'StoreType')) 

    df.index.name = 'index'
    df = df.reset_index(drop=True)

    try:
        if storeType == 1:
            collection = getCollection(database, CollectionKey)
            collection.remove()
            writeToCollection(collection, df)

        if storeType == 2:
            csv_dir = root_path + "/" + config.get('Paths', database) + config.get('Paths', 'STOCK_SHARE')
            writeToCSV(csv_dir, CollectionKey, df)
    
    except Exception as e:
        print("storeStockList Exception", e)


def queryStockPublishDay(root_path, database, symbol):
    CollectionKey = "StockPublishDay"
    config = getConfig(root_path)
    storeType = int(config.get('Setting', 'StoreType'))

    try:
        if storeType == 1:
            collection = getCollection(database, CollectionKey)
            df = readFromCollection(collection, {})
            if df.empty == False:
                publishDay = df[df['Code'] == symbol]
                if len(publishDay) == 1:
                    return publishDay['Date'].values[0]
            return ''

        if storeType == 2:
            csv_dir = root_path + "/" + config.get('Paths', database) + config.get('Paths', 'STOCK_SHARE')
            filename = csv_dir + CollectionKey + '.csv'
            if os.path.exists(filename):
                df = pd.read_csv(filename)
                publishDay = df[df['Code'] == symbol]
                if len(publishDay) == 1:
                    return publishDay['Date'].values[0]
            return ''

    except Exception as e:
        print("queryStockPublishDay Exception", e)
        return ''
    return ''

def storePublishDay(root_path, database, symbol, date):
    CollectionKey = "StockPublishDay"
    config = getConfig(root_path)
    storeType = int(config.get('Setting', 'StoreType'))

    try:
        if storeType == 1:
            collection = getCollection(database, CollectionKey)

            df = pd.DataFrame(columns = ['Code', 'Date'])
            df.index.name = 'index'
            df.loc[len(df)] = [symbol, date]
            writeToCollection(collection, df)

        if storeType == 2:
            csv_dir = root_path + "/" + config.get('Paths', database) + config.get('Paths', 'STOCK_SHARE')
            if os.path.exists(csv_dir) == False:
                os.makedirs(csv_dir)
            filename = csv_dir + CollectionKey + '.csv'
            if os.path.exists(filename):
                df = pd.read_csv(filename, index_col=["index"])
                publishDate = df[df['Code'] == symbol]
                if publishDate.empty:
                    df.loc[len(df)] = [symbol, date]
            else: 
                df = pd.DataFrame(columns = ['Code', 'Date'])
                df.index.name = 'index'
                df.loc[len(df)] = [symbol, date]
            df.to_csv(filename)
    
    except Exception as e:
        print("storePublishDay Exception", e)

def queryStock(root_path, database, symbol):
    CollectionKey = 'StockDaily_' + symbol[0]
    config = getConfig(root_path)
    storeType = int(config.get('Setting', 'StoreType'))
    lastUpdateTime = pd.Timestamp('1970-01-01')

    try:
        if storeType == 1:
            collection = getCollection(database, CollectionKey)
            #queryString = { "Symbol" : symbol }
            collection = collection[symbol]
            df = readFromCollection(collection, {})
            if df.empty: return pd.DataFrame(), lastUpdateTime
            del df['_id']
            lastUpdateTime = pd.Timestamp(df['lastUpdate'].iloc[0])
            df = df.set_index('Date')
            return df, lastUpdateTime
            
        if storeType == 2:
            csv_dir = root_path + "/" + config.get('Paths', database)
            filename = csv_dir + symbol + '.csv'
            df = pd.read_csv(filename, index_col=["Date"])
            if 'lastUpdate' in df:
                lastUpdateTime = pd.Timestamp(df['lastUpdate'].iloc[0])
            return df, lastUpdateTime
        
    except Exception as e:
        print("queryStock Exception", e)
        return pd.DataFrame(), lastUpdateTime

    return pd.DataFrame(), lastUpdateTime


def storeStock(root_path, database, symbol, df):
    CollectionKey = 'StockDaily_' + symbol[0]
    config = getConfig(root_path)
    storeType = int(config.get('Setting', 'StoreType'))
    now_date = datetime.datetime.now().strftime("%Y-%m-%d")
    df.index.name = 'Date'
    
    if 'Date' in df: df.set_index('Date')  
    df['lastUpdate'] = now_date
    df.index = df.index.astype(str)
    df.sort_index(ascending=True, inplace=True)

    try:
        if storeType == 1:
            collection = getCollection(database, CollectionKey)
            collection = collection[symbol]
            # df['Symbol'] = symbol
            df = df.reset_index()
            writeToCollection(collection, df)

        if storeType == 2:
            csv_dir = root_path + "/" + config.get('Paths', database)
            writeToCSV(csv_dir, symbol, df)

    except Exception as e:
        print(df)
        print(symbol)
        print("storeStock Exception", e)

def queryNews(root_path, database, symbol):
    CollectionKey = symbol
    config = getConfig(root_path)
    storeType = int(config.get('Setting', 'StoreType'))

    try:
        if storeType == 1:
            collection = getCollection(database, CollectionKey)
            df = readFromCollection(collection, {})
            if df.empty: return pd.DataFrame()
            del df['_id']
            df = df.set_index('Date')
            return df

        if storeType == 2:
            dir = root_path + "/" + config.get('Paths', database)
            filename = dir + CollectionKey + '.csv'
            return pd.read_csv(filename)
    
    except Exception as e:
        print("queryNews Exception", e)
        return pd.DataFrame()

    return pd.DataFrame()


def storeNews(root_path, database, symbol, df):
    CollectionKey = symbol
    config = getConfig(root_path)
    storeType = int(global_config.get('Setting', 'StoreType'))
    now_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    df = df.drop_duplicates(subset=['Uri'], keep='first')
    df.set_index(['Date'], inplace=True)
    df.sort_index(ascending=True, inplace=True)
    
    try:
        if storeType == 1:
            collection = getCollection(database, CollectionKey)
            df = df.reset_index()
            writeToCollection(collection, df)

        if storeType == 2:
            csv_dir = root_path + "/" + config.get('Paths', database)
            writeToCSV(csv_dir, CollectionKey, df)
    
    except Exception as e:
        print("storeNews Exception", e)


def queryEarnings(root_path, database, date):
    CollectionKey = date
    config = getConfig(root_path)
    storeType = int(config.get('Setting', 'StoreType'))

    try:
        if storeType == 1:
            collection = getCollection(database, CollectionKey)
            return readFromCollection(collection, {})
        
        if storeType == 2:
            dir = root_path + "/" + config.get('Paths', database)
            filename = dir + CollectionKey + ".csv"
            return pd.read_csv(filename)

    except Exception as e:
        print("queryEarnings Exception", e)
        return pd.DataFrame()

    return pd.DataFrame()


def storeEarnings(root_path, database, date, df):
    CollectionKey = date
    config = getConfig(root_path)
    storeType = int(config.get('Setting', 'StoreType'))

    now_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    try:
        if storeType == 1:
            collection = getCollection(database, CollectionKey)
            writeToCollection(collection, df)

        if storeType == 2:
            csv_dir = root_path + "/" + config.get('Paths', database)
            writeToCSV(csv_dir, CollectionKey, df)

    except Exception as e:
        print("storeNews Exception", e)


def queryTweets(root_path, database, symbol, col):
    CollectionKey = symbol
    config = getConfig(root_path)
    storeType = int(config.get('Setting', 'StoreType'))

    try:
        if storeType == 1:
            collection = getCollection(database, CollectionKey)
            return readFromCollection(collection, {})

        if storeType == 2:
            dir = root_path + "/" + config.get('Paths', database)
            filename = dir + CollectionKey + ".csv"
            return pd.read_csv(filename, usecols=col)

    except Exception as e:
        print("queryTweets Exception", e)
        return pd.DataFrame()

    return pd.DataFrame()


def storeTweets(root_path, database, symbol, df):
    CollectionKey = symbol
    config = getConfig(root_path)
    storeType = int(config.get('Setting', 'StoreType'))

    now_date = datetime.datetime.now().strftime("%Y-%m-%d")

    df = df.drop_duplicates(keep='last')
    df = df.sort_values(['Date'], ascending=[False]).reset_index(drop=True)
    
    try:
        if storeType == 1:
            collection = getCollection(database, CollectionKey)
            writeToCollection(collection, df)
        
        if storeType == 2:
            csv_dir = root_path + "/" + config.get('Paths', database)
            writeToCSV(csv_dir, CollectionKey, df)

    except Exception as e:
        print("storeTweets Exception", e)


def queryCoorelation(root_path, database):
    CollectionKey = "us_company_coorelation"
    config = getConfig(root_path)
    storeType = int(global_config.get('Setting', 'StoreType'))

    try:
        if storeType == 1:
            collection = getCollection(database, CollectionKey)
            return readFromCollection(collection, {})
        
        if storeType == 2:
            dir = root_path + "/" + config.get('Paths', database)
            filename = dir + CollectionKey + ".csv"
            return pd.read_csv(filename, index_col=0)

    except Exception as e:
        print("queryCoorelation Exception", e)
        return pd.DataFrame()

    return pd.DataFrame()


def storeCoorelation(root_path, database, df):
    CollectionKey = "us_company_coorelation"
    config = getConfig(root_path)
    storeType = int(global_config.get('Setting', 'StoreType'))

    now_date = datetime.datetime.now().strftime("%Y-%m-%d")

    try:
        if storeType == 1:
            collection = getCollection(database, CollectionKey)
            writeToCollection(collection, df)
        
        if storeType == 2:
            csv_dir = root_path + "/" + config.get('Paths', database)
            writeToCSV(csv_dir, CollectionKey, df)
    
    except Exception as e:
        print("storeCoorelation Exception", e)