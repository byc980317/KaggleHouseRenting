import numpy as np
import pandas as pd
from scipy import sparse
import xgboost as xgb
import random
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import log_loss
from FeatureExtract import get_stats
from sklearn.feature_extraction.text import CountVectorizer
from xgboost import XGBClassifier

train_df = pd.read_json('train.json')
test_df = pd.read_json('test.json')

# add price feature
train_df["logprice"] = np.log(train_df["price"])
test_df["logprice"] = np.log(test_df["price"])
train_df["price_bed"] = train_df["price"] / train_df["bedrooms"]
test_df["price_bed"] = test_df["price"] / test_df["bedrooms"]
train_df["price_bath"] = train_df["price"] / train_df["bathrooms"]
test_df["price_bath"] = test_df["price"] / test_df["bathrooms"]
train_df["price_latitue"] = (train_df["price"])/ (train_df["latitude"]+1.0)
test_df["price_latitue"] =  (test_df["price"])/ (test_df["latitude"]+1.0)
train_df["price_longtitude"] = (train_df["price"])/ (train_df["longitude"]-1.0)
test_df["price_longtitude"] =  (test_df["price"])/ (test_df["longitude"]-1.0)


# add room feature
train_df["room_sum"] = train_df["bedrooms"] + train_df["bathrooms"]
test_df["room_sum"] = test_df["bedrooms"] + test_df["bathrooms"]
train_df["room_diff"] = train_df["bedrooms"] - train_df["bathrooms"]
test_df["room_diff"] = test_df["bedrooms"] - test_df["bathrooms"]
train_df['price_per_room'] = train_df['price'] / train_df['room_sum']
test_df['price_per_room'] = test_df['price'] / test_df['room_sum']
train_df["num_furniture"] = train_df["room_sum"].apply(lambda x:  str(x) if float(x)<9.5 else '10')
test_df["num_furniture"] = test_df["room_sum"].apply(lambda x:  str(x) if float(x)<9.5 else '10')

# add length feature
train_df["num_photos"] = train_df["photos"].apply(len)
test_df["num_photos"] = test_df["photos"].apply(len)

train_df["num_features"] = train_df["features"].apply(len)
test_df["num_features"] = test_df["features"].apply(len)

train_df["num_description_words"] = train_df["description"].apply(lambda x: len(x.split(" ")))
test_df["num_description_words"] = test_df["description"].apply(lambda x: len(x.split(" ")))

# add time feature
train_df["created"] = pd.to_datetime(train_df["created"])
test_df["created"] = pd.to_datetime(test_df["created"])
train_df["created_year"] = train_df["created"].dt.year
test_df["created_year"] = test_df["created"].dt.year
train_df["created_month"] = train_df["created"].dt.month
test_df["created_month"] = test_df["created"].dt.month
train_df["created_day"] = train_df["created"].dt.day
test_df["created_day"] = test_df["created"].dt.day
train_df["created_hour"] = train_df["created"].dt.hour
test_df["created_hour"] = test_df["created"].dt.hour
train_df["total_days"] = (train_df["created_month"] -4.0)*30 + train_df["created_day"] +  train_df["created_hour"] /25.0
test_df["total_days"] = (test_df["created_month"] -4.0)*30 + test_df["created_day"] +  test_df["created_hour"] /25.0
train_df["diff_rank"]= train_df["total_days"]/train_df["listing_id"]
test_df["diff_rank"]= test_df["total_days"]/test_df["listing_id"]

train_df["pos"] = train_df.longitude.round(3).astype(str) + '_' + train_df.latitude.round(3).astype(str)
test_df["pos"] = test_df.longitude.round(3).astype(str) + '_' + test_df.latitude.round(3).astype(str)

vals = train_df['pos'].value_counts()
dvals = vals.to_dict()
train_df["density"] = train_df['pos'].apply(lambda x: dvals.get(x, vals.min()))
test_df["density"] = test_df['pos'].apply(lambda x: dvals.get(x, vals.min()))

features_to_use = ["bathrooms", "bedrooms", "latitude", "longitude", "price", "price_bed", "price_bath", "price_per_room", "logprice",
                   "density",
                   "num_photos", "num_features", "num_description_words", "listing_id", "created_year", "created_month",
                   "created_day", "created_hour", "room_sum", "room_diff", "price_latitue", "price_longtitude", "total_days", "diff_rank"]

train_stack_list, test_stack_list = [],[]
for target_col in features_to_use:
    tmp_train, tmp_test = get_stats(train_df,test_df,target_column=target_col)
    train_stack_list.append(tmp_train)
    test_stack_list.append(tmp_test)
train_stack_list = np.array(train_stack_list)
test_stack_list = np.array(test_stack_list)

index = list(range(train_df.shape[0]))
random.shuffle(index)
a = [np.nan] * len(train_df)
b = [np.nan] * len(train_df)
c = [np.nan] * len(train_df)

for i in range(5):
    building_level = {}
    for j in train_df['manager_id'].values:
        building_level[j] = [0, 0, 0]

    test_index = index[int((i * train_df.shape[0]) / 5):int(((i + 1) * train_df.shape[0]) / 5)]
    train_index = list(set(index).difference(test_index))

    for j in train_index:
        temp = train_df.iloc[j]
        if temp['interest_level'] == 'low':
            building_level[temp['manager_id']][0] += 1
        if temp['interest_level'] == 'medium':
            building_level[temp['manager_id']][1] += 1
        if temp['interest_level'] == 'high':
            building_level[temp['manager_id']][2] += 1

    for j in test_index:
        temp = train_df.iloc[j]
        if sum(building_level[temp['manager_id']]) != 0:
            a[j] = building_level[temp['manager_id']][0] * 1.0 / sum(building_level[temp['manager_id']])
            b[j] = building_level[temp['manager_id']][1] * 1.0 / sum(building_level[temp['manager_id']])
            c[j] = building_level[temp['manager_id']][2] * 1.0 / sum(building_level[temp['manager_id']])

train_df['manager_level_low'] = a
train_df['manager_level_medium'] = b
train_df['manager_level_high'] = c

a = []
b = []
c = []
building_level = {}
for j in train_df['manager_id'].values:
    building_level[j] = [0, 0, 0]

for j in range(train_df.shape[0]):
    temp = train_df.iloc[j]
    if temp['interest_level'] == 'low':
        building_level[temp['manager_id']][0] += 1
    if temp['interest_level'] == 'medium':
        building_level[temp['manager_id']][1] += 1
    if temp['interest_level'] == 'high':
        building_level[temp['manager_id']][2] += 1

for i in test_df['manager_id'].values:
    if i not in building_level.keys():
        a.append(np.nan)
        b.append(np.nan)
        c.append(np.nan)
    else:
        a.append(building_level[i][0] * 1.0 / sum(building_level[i]))
        b.append(building_level[i][1] * 1.0 / sum(building_level[i]))
        c.append(building_level[i][2] * 1.0 / sum(building_level[i]))
test_df['manager_level_low'] = a
test_df['manager_level_medium'] = b
test_df['manager_level_high'] = c

features_to_use.append('manager_level_low')
features_to_use.append('manager_level_medium')
features_to_use.append('manager_level_high')

categorical = ["display_address", "manager_id", "building_id", "street_address", "num_furniture"]
# lencat=len(categorical)
# for f in range (0,lencat):
#     for s in range (f+1,lencat):
#         train_df[categorical[f] + "_" +categorical[s]] =train_df[categorical[f]]+"_" + train_df[categorical[s]]
#         test_df[categorical[f] + "_" +categorical[s]] =test_df[categorical[f]]+"_" + test_df[categorical[s]]
#         categorical.append(categorical[f] + "_" +categorical[s])

for f in categorical:
    if train_df[f].dtype == 'object':
        lbl = LabelEncoder()
        lbl.fit(list(train_df[f].values) + list(test_df[f].values))
        train_df[f] = lbl.transform(list(train_df[f].values))
        test_df[f] = lbl.transform(list(test_df[f].values))
        features_to_use.append(f)

train_df['features'] = train_df["features"].apply(lambda x: " ".join(["_".join(i.split(" ")) for i in x]))
test_df['features'] = test_df["features"].apply(lambda x: " ".join(["_".join(i.split(" ")) for i in x]))

tfidf = CountVectorizer(stop_words='english', max_features=200)
tr_sparse = tfidf.fit_transform(train_df["features"])
te_sparse = tfidf.transform(test_df["features"])

# stack features together
train_X = train_df[features_to_use]
test_X = test_df[features_to_use]
for i in train_stack_list:
    train_X = sparse.hstack([train_X,i])
for i in test_stack_list:
    test_X = sparse.hstack([test_X,i])
train_X = sparse.hstack([train_X, tr_sparse]).tocsr()
test_X = sparse.hstack([test_X, te_sparse]).tocsr()
print(train_X.shape)

# mapping labels
target_num_map = {'high': 0, 'medium': 1, 'low': 2}
train_y = np.array(train_df['interest_level'].apply(lambda x: target_num_map[x]))

# stacknet
clf1 = XGBClassifier(objective = 'multi:softprob', max_depth=5,silent = True, booster='gbtree', subsample=0.9, \
              colsample_bytree=0.7, reg_alpha=0.5, seed = 321)
clf2 = XGBClassifier()
models = [
    ## first layer
    [clf1],
    ## second layer
    [clf2]]
stacknet = StackNetClassifier(models, metric="logloss", folds=4, restacking=False, use_retraining=True, \
                              use_proba=True, random_state=12345,n_jobs=1, verbose=1)
stacknet.fit(train_X, train_y)
preds = stacknet.predict_proba(test_x)



out_df = pd.DataFrame(preds)
out_df.columns = ["high", "medium", "low"]
out_df["listing_id"] = test_df.listing_id.values
out_df.head()
