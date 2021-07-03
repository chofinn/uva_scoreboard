from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import os
from flask_cors import CORS
#from fbauth import check_token
import re
#from flask_mail import Mail, Message
import json


app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite')
db = SQLAlchemy(app)
ma = Marshmallow(app)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'




class Quest(db.Model):
    quest_id = db.Column(db.Integer, primary_key=True)
    qid = db.Column(db.String(100), nullable=False)
    status = db.Column(db.DateTime)
    submit_time = db.Column(db.String(100), nullable=False)
    run_time = db.Column(db.Integer)
    submitter = db.Column(db.DateTime)
    platform = db.Column(db.String(100), nullable=False)
    
    
    def __init__(self, qid, status, submit_time, run_time, submitter, platform ):
        self.qid = qid
        self.status = status
        self.submit_time = submit_time
        self.run_time = run_time
        self.submitter = submitter
        self.platform  = platform 

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String)
    user_name = db.Column(db.String(20), nullable=False)
    ac = db.Column(db.String(100), nullable=False)
    total = db.Column(db.String)

    def __init__(self, user_name, uid, ac, total):
        self.user_name = user_name
        self.uid = uid
        self.ac = ac
        self.total = total


class QuestSchema(ma.Schema):
    class Meta:
        # Fields to expose
        fields = ('qid', 'status', 'submit_time', 'run_time', 'submitter', 'platform')

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
    columns = ['quest_id', 'quest_name', 'quest_time', 'quest_place', 'quest_duration', 'end_reservation_date', 'info_url', 'tags']
    col_values = []
    for c in columns:
        if c in request.values:
            if c in ['quest_time', 'end_reservation_date']:
                col_values.append(toDtObject(request.values[c]))
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
    columns = ['quest_id', 'quest_name', 'quest_time', 'quest_place', 'quest_duration', 'end_reservation_date', 'info_url', 'tags']
    for c in columns:
        if c in request.values:
            if c in ['quest_time', 'end_reservation_date']:
                setattr(quest, c, toDtObject(request.values[c]))
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

# endpoint to get quest for certain user
@app.route("/user_quests", methods=["GET"])
def user_quests(**kwargs):
    current_user = kwargs['user']
    user = User.query.filter_by(uid=current_user)
    
    all_quests = Quest.query.all()
    reserved_quests = json.loads(getattr(user, 'quests'))
    reservation = {}
    for e in all_quests:
        if getattr(e, 'quest_id') in reserved_quests:
            reservation[getattr(e, 'quest_id')] = True
        else:
            reservation[getattr(e, 'quest_id')] = False

    result = quests_schema.dump(all_quests)

    for t in result:
        t['is_reserved'] = reservation[t['quest_id']]

    result_json = user_quests_schema.jsonify(result)

    return result_json

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#          user CRUD             #
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# endpoint to create new user
@app.route("/user", methods=["POST"])
def add_user():
    columns = ['user_name', 'uid']
    col_values = []
    for c in columns:
        if c in request.values:
            col_values.append(request.values[c])
        else:
            col_values.append(None)
    col_values.append(encrypt_pw(request.values['user_pw']))
    col_values.append('[]')
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
    columns = ['user_name', 'uid', 'user_pw', 'quests']
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


@app.route('/reserve', methods=["POST"])
def reserve(**kwargs):
    current_user = kwargs['user']
    user = User.query.filter_by(uid=current_user)
    quest_id = int(request.values["quest_id"])

    #success = reserve_activity(quest_id)
    success = True
    
    if success:
        quests = json.loads(getattr(user, 'quests'))
        quests.append(quest_id)
        setattr(user, 'quests', json.dumps(quests))
        db.session.commit()
        return {'message': 'reserve successful'},200
    else:
        return {'message': 'reserve failed'},500

@app.route('/cancel', methods=["POST"])
def cancel(**kwargs):
    current_user = kwargs['user']
    user = User.query.filter_by(uid=current_user)
    quest_id = int(request.values["quest_id"])

    #success = cancel_activity(quest_id)
    success = True
    
    if success:
        quests = json.loads(getattr(user, 'quests'))
        quests.remove(quest_id)
        setattr(user, 'quests', json.dumps(quests))
        db.session.commit()
        return {'message': 'cancel successful'},200
    else:
        return {'message': 'cancel failed'},500

if __name__ == '__main__':
    app.run(debug = True, host="0.0.0.0", port=20002)
    app.run(debug=True)
