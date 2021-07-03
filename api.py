from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import os
from flask_cors import CORS
import re
import json
from datetime import datetime
from urllib.request import urlopen

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite')
db = SQLAlchemy(app)
ma = Marshmallow(app)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

status_code = {
    10 : "Submission error",
    15 : "Can't be judged",
    20 : 'In queue',
    30 : 'Compile error',
    35 : 'Restricted function',
    40 : 'Runtime error',
    45 : 'Output limit',
    50 : 'Time limit',
    60 : 'Memory limit',
    70 : 'Wrong answer',
    80 : 'PresentationE',
    90 : 'Accepted',
}
def get_info(user_name):
    uva_id = str(json.loads(urlopen('https://uhunt.onlinejudge.org/api/uname2uid/' + user_name).read()))
    response = urlopen('https://uhunt.onlinejudge.org/api/subs-user/'+ uva_id).read()

    results = json.loads(response).get("subs")
    ac = 0
    for r in results:
        col_values = []

        probs = json.loads(urlopen('https://uhunt.onlinejudge.org/api/p/id/'+ str(r[1])).read())
        col_values.append(probs['num'])
        col_values.append(probs['title'])
        col_values.append(status_code[r[2]])
        col_values.append(datetime.utcfromtimestamp(r[4]))
        col_values.append(r[3])
        col_values.append(user_name)
        col_values.append('UVa')
        if(r[2] == 90):
            ac += 1

        new_quest = Quest(*col_values)
        db.session.add(new_quest)
        db.session.commit()

    return ac, len(results)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#           Tables          #
#~~~~~~~~~~~~~~~~~~~~~~~~~~~#
class Quest(db.Model):
    quest_id = db.Column(db.Integer, primary_key=True)
    qid = db.Column(db.Integer)
    quest_name = db.Column(db.String(100))
    status = db.Column(db.String(100))
    submit_time = db.Column(db.DateTime)
    run_time = db.Column(db.Float)
    submitter = db.Column(db.String(50))
    platform = db.Column(db.String(100))
    
    def __init__(self, qid, quest_name, status, submit_time, run_time, submitter, platform):
        self.qid = qid
        self.quest_name = quest_name
        self.status = status
        self.submit_time = submit_time
        self.run_time = run_time
        self.submitter = submitter
        self.platform  = platform 


class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String)
    user_name = db.Column(db.String(20))
    ac = db.Column(db.Integer)
    total = db.Column(db.Integer)

    def __init__(self, user_name, uid, ac, total):
        self.user_name = user_name
        self.uid = uid
        self.ac = ac
        self.total = total


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#           Schemas          #
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
class QuestSchema(ma.Schema):
    class Meta:
        # Fields to expose
        fields = ('qid', 'quest_name', 'status', 'submit_time', 'run_time', 'submitter', 'platform')

class UserSchema(ma.Schema):
    class Meta:
        # Fields to expose
        fields = ('user_name', 'uid', 'ac', 'total')

quest_schema = QuestSchema()
quests_schema = QuestSchema(many=True)

user_schema = UserSchema()
users_schema = UserSchema(many=True)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#           Quest CRUD          #
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# endpoint to create new quest
@app.route("/quest", methods=["POST"])
#@check_token
def add_quest():
    columns = ['qid', 'quest_name', 'status', 'submit_time', 'run_time', 'submitter', 'platform']
    col_values = []
    for c in columns:
        if c in request.values:
            if c in ['submit_time']:
                col_values.append(datetime.utcfromtimestamp(int(request.values[c])))
            else:
                col_values.append(request.values[c])
        else:
            col_values.append("None")
        
    new_quest = Quest(*col_values)
    
    db.session.add(new_quest)
    db.session.commit()

    return {'message': 'successfully create new quest'},200

# endpoint to show all quests
@app.route("/quest", methods=["GET"])
def get_quest():
    all_quests = Quest.query.all()
    result = quests_schema.dump(all_quests)

    result_json = quests_schema.jsonify(result)

    return result_json

# endpoint to get quest detail by id
@app.route("/quest/<id>", methods=["GET"])
def quest_detail(id):
    quest = Quest.query.get(id)

    return quest_schema.jsonify(quest)


# endpoint to update quest
@app.route("/quest/<id>", methods=["PUT"])
#@check_token
def quest_update(id):
    quest = Quest.query.get(id)
    columns = ['qid', 'quest_name', 'status', 'submit_time', 'run_time', 'submitter', 'platform']
    for c in columns:
        if c in request.values:
            if c in ['submit_time']:
                setattr(quest, c, datetime.utcfromtimestamp(int(request.values[c])))
            else:
                setattr(quest, c, request.values[c])
            

    db.session.commit()
    #return quest_schema.jsonify(quest)
    return {'message': 'successfully update quest'}, 200


# endpoint to delete quest
@app.route("/quest/<id>", methods=["DELETE"])
#@check_token
def quest_delete(id):
    quest = Quest.query.get(id)

    db.session.delete(quest)
    db.session.commit()

    # return quest_schema.jsonify(quest)
    return {'message': 'successfully delete quest'}, 200

@app.route("/get_user_quest/<name>", methods=["GET"])
def get_user_quest(name):
    quests = Quest.query.filter_by(submitter=name)
    result = quests_schema.dump(quests)

    result_json = quests_schema.jsonify(result)

    return result_json


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#          user CRUD             #
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# endpoint to create new user
@app.route("/user", methods=["POST"])
def add_user():
    columns = ['user_name', 'uid', 'ac', 'total']
    col_values = []
    for c in columns:
        if c in request.values:
            col_values.append(request.values[c])
        else:
            col_values.append(None)
    new_user = User(*col_values)
    
    db.session.add(new_user)
    db.session.commit()

    return {'message': 'successfully create new user'},200


# endpoint to show all users
@app.route("/user", methods=["GET"])
def get_user():
    all_users = User.query.all()
    result = users_schema.dump(all_users)

    result_json = users_schema.jsonify(result)

    return result_json

# endpoint to get user detail by id
@app.route("/user/<id>", methods=["GET"])
def user_detail(id):
    user = User.query.get(id)

    return user_schema.jsonify(user)


# endpoint to update user
@app.route("/user/<id>", methods=["PUT"])
def user_update(id):
    user = User.query.get(id)
    columns = ['user_name', 'uid', 'ac', 'total']
    for c in columns:
        if c in request.values:
            setattr(user, c, request.values[c])

    db.session.commit()
    return {'message': 'successfully update user'}, 200


# endpoint to delete user
@app.route("/user/<id>", methods=["DELETE"])
def user_delete(id):
    user = User.query.get(id)

    db.session.delete(user)
    db.session.commit()

    return {'message': 'successfully delete user'}, 200

@app.route("/fetch_data", methods=["POST"])
def fetch_data():
    name = request.values['user_name']
    user = User.query.filter_by(uid=name).first()
    ac, total = get_info(getattr(user, 'user_name'))
    setattr(user, 'ac', ac)
    setattr(user, 'total', total)
    db.session.commit()


if __name__ == '__main__':
    # app.run(debug = True, host="0.0.0.0", port=8080)
    app.run(debug=True)
