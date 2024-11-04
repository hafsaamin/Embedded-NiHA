from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import openai
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import json
import traceback
import logging
import os
import speech_recognition as sr  # Add this import for speech recognition

app = Flask(__name__)
CORS(app, origins=['http://localhost:3000'])  # Adjust the origin as needed

# Set your OpenAI API key
OPENAI_API_KEY = "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"
openai.api_key = OPENAI_API_KEY  # Set the API key for OpenAI

# MongoDB connection
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client['chatbot_db']
conversation_collection = db['conversations']

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/chat/<username>', methods=['POST'])
def chat(username):
    data = request.json
    conversation_id = data.get('conversation_id')
    messages = data.get('messages', [])

    if not messages:
        return 'No messages provided', 400

    def generate():
        nonlocal conversation_id, username
        try:
            # Call OpenAI API with the entire conversation history
            response = openai.ChatCompletion.create(
                model='gpt-3.5-turbo',
                messages=messages,
                stream=True
            )

            bot_response = ''
            for chunk in response:
                if 'choices' in chunk and len(chunk['choices']) > 0:
                    content = chunk['choices'][0].get('delta', {}).get('content')
                    if content:
                        bot_response += content
                        yield f"data: {json.dumps({'content': content})}\n\n"

            # Save the conversation after generating the full response
            if not conversation_id:
                conversation = {
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'messages': messages + [{'role': 'assistant', 'content': bot_response}],
                    'username': username
                }
                result = conversation_collection.insert_one(conversation)
                conversation_id = str(result.inserted_id)
                logger.info(f"New conversation created with ID: {conversation_id}")
            else:
                conversation_collection.update_one(
                    {'_id': ObjectId(conversation_id), 'username': username},
                    {
                        '$set': {
                            'messages': messages + [{'role': 'assistant', 'content': bot_response}],
                            'updated_at': datetime.now(),
                            'username': username
                        }
                    }
                )
                logger.info(f"Conversation updated with ID: {conversation_id}")

            yield f"data: {json.dumps({'conversation_id': conversation_id})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            error_details = traceback.format_exc()
            yield f"data: {json.dumps({'error': str(e), 'details': error_details})}\n\n"
            yield "data: [DONE]\n\n"

    return Response(generate(), content_type='text/event-stream')

@app.route('/conversations/<username>', methods=['GET'])
def get_conversations(username):
    try:
        conversations = list(conversation_collection.find(
            {'username': username},
            {'messages': {'$slice': -1}, 'created_at': 1, 'updated_at': 1}
        ))
        for conv in conversations:
            conv['_id'] = str(conv['_id'])
            conv['last_message'] = conv['messages'][0]['content'] if conv.get('messages') else ''
            del conv['messages']
        logger.info(f"Retrieved {len(conversations)} conversations for user {username}")
        return jsonify(conversations)
    except Exception as e:
        logger.error(f"Error retrieving conversations for user {username}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve conversations'}), 500

@app.route('/conversation/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    try:
        conversation = conversation_collection.find_one({'_id': ObjectId(conversation_id)})
        if conversation:
            conversation['_id'] = str(conversation['_id'])
            return jsonify(conversation)
        return jsonify({'error': 'Conversation not found'}), 404
    except Exception as e:
        logger.error(f"Error retrieving conversation {conversation_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve conversation'}), 500

@app.route('/conversation/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    try:
        result = conversation_collection.delete_one({'_id': ObjectId(conversation_id)})
        if result.deleted_count:
            return jsonify({'message': 'Conversation deleted successfully'}), 200
        else:
            return jsonify({'message': 'Conversation not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id}: {str(e)}")
        return jsonify({'error': 'Failed to delete conversation'}), 500

@app.route('/conversations', methods=['POST'])
def create_conversation():
    data = request.json
    username = data.get('username', 'Guest')

    try:
        conversation = {
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'messages': [],
            'username': username
        }
        result = conversation_collection.insert_one(conversation)
        conversation_id = str(result.inserted_id)
        logger.info(f"New conversation created with ID: {conversation_id}")
        return jsonify({'conversation_id': conversation_id}), 201
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        return jsonify({'error': 'Failed to create conversation'}), 500

@app.route('/chat_sessions/<username>', methods=['GET'])
def get_chat_sessions(username):
    try:
        # Fetch conversations for the specific user
        conversations = list(conversation_collection.find({'username': username}))
        for conv in conversations:
            conv['_id'] = str(conv['_id'])
        return jsonify(conversations)
    except Exception as e:
        logger.error(f"Error retrieving chat sessions for user {username}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve chat sessions'}), 500

@app.route('/groups/<username>', methods=['GET', 'POST'])
def manage_groups(username):
    if request.method == 'GET':
        try:
            groups = list(db.groups.find({'username': username}))
            for group in groups:
                group['_id'] = str(group['_id'])
            return jsonify(groups)
        except Exception as e:
            logger.error(f"Error retrieving groups for user {username}: {str(e)}")
            return jsonify({'error': 'Failed to retrieve groups'}), 500
    
    elif request.method == 'POST':
        data = request.json
        group_name = data.get('name')
        if not group_name:
            return jsonify({'error': 'Group name is required'}), 400
        
        try:
            new_group = {
                'name': group_name,
                'username': username,
                'conversations': [],
                'createdAt': datetime.now()
            }
            result = db.groups.insert_one(new_group)
            new_group['_id'] = str(result.inserted_id)
            return jsonify(new_group), 201
        except Exception as e:
            logger.error(f"Error creating group for user {username}: {str(e)}")
            return jsonify({'error': 'Failed to create group'}), 500

@app.route('/groups/<group_id>/conversations', methods=['POST'])
def add_conversation_to_group(group_id):
    data = request.json
    conversation_id = data.get('conversation_id')
    if not conversation_id:
        return jsonify({'error': 'Conversation ID is required'}), 400
    
    try:
        # Add the conversation to the group
        db.groups.update_one(
            {'_id': ObjectId(group_id)},
            {'$addToSet': {'conversations': ObjectId(conversation_id)}}
        )
        # Optionally, remove the conversation from the main conversations collection
        db.conversations.delete_one({'_id': ObjectId(conversation_id)})
        
        return jsonify({'message': 'Conversation added to group successfully'}), 200
    except Exception as e:
        logger.error(f"Error adding conversation to group {group_id}: {str(e)}")
        return jsonify({'error': 'Failed to add conversation to group'}), 500

@app.route('/groups/<group_id>/conversations', methods=['GET'])
def get_group_conversations(group_id):
    try:
        group = db.groups.find_one({'_id': ObjectId(group_id)})
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        conversations = list(conversation_collection.find({'_id': {'$in': group['conversations']}}))
        for conv in conversations:
            conv['_id'] = str(conv['_id'])
        return jsonify(conversations)
    except Exception as e:
        logger.error(f"Error retrieving conversations for group {group_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve group conversations'}), 500

@app.route('/groups/<username>', methods=['POST'])
def create_group(username):
    data = request.json
    group_name = data.get('name')
    
    if not group_name:
        return jsonify({'error': 'Group name is required'}), 400

    new_group = {
        'name': group_name,
        'username': username,
        'conversations': [],
        'createdAt': datetime.now()
    }

    try:
        result = db.groups.insert_one(new_group)
        new_group['_id'] = str(result.inserted_id)
        return jsonify(new_group), 201
    except Exception as e:
        logging.error(f"Error creating group: {str(e)}")
        return jsonify({'error': 'Failed to create group'}), 500

@app.route('/groups/<username>/<group_id>', methods=['PUT'])
def rename_group(username, group_id):
    data = request.json
    new_name = data.get('name')
    
    if not new_name:
        return jsonify({'error': 'New group name is required'}), 400

    try:
        result = db.groups.update_one(
            {'_id': ObjectId(group_id), 'username': username},
            {'$set': {'name': new_name}}
        )
        if result.matched_count == 0:
            return jsonify({'error': 'Group not found or does not belong to user'}), 404
        
        return jsonify({'message': 'Group renamed successfully'}), 200
    except Exception as e:
        logger.error(f"Error renaming group {group_id}: {str(e)}")
        return jsonify({'error': 'Failed to rename group'}), 500

@app.route('/groups/<username>/<group_id>', methods=['DELETE'])
def delete_group(username, group_id):
    try:
        result = db.groups.delete_one({'_id': ObjectId(group_id), 'username': username})
        if result.deleted_count == 0:
            return jsonify({'error': 'Group not found or does not belong to user'}), 404
        
        return jsonify({'message': 'Group deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting group {group_id}: {str(e)}")
        return jsonify({'error': 'Failed to delete group'}), 500

@app.route('/groups/<group_id>/add-chat', methods=['POST'])
def add_chat_to_group(group_id):
    try:
        data = request.json
        chat_id = data.get('chatId')
        username = data.get('username')

        if not chat_id:
            return jsonify({'error': 'Chat ID is required'}), 400

        # Find the chat and verify it belongs to the user
        chat = conversation_collection.find_one({
            '_id': ObjectId(chat_id),
            'username': username
        })

        if not chat:
            return jsonify({'error': 'Chat not found or unauthorized'}), 404

        # Add chat to group's conversations array
        result = db.groups.update_one(
            {'_id': ObjectId(group_id)},
            {'$addToSet': {'conversations': ObjectId(chat_id)}}
        )

        if result.modified_count == 0:
            return jsonify({'error': 'Group not found or chat already in group'}), 404

        return jsonify({'message': 'Chat added to group successfully'}), 200

    except Exception as e:
        logger.error(f"Error adding chat to group: {str(e)}")
        return jsonify({'error': 'Failed to add chat to group'}), 500

if __name__ == '__main__':
    app.run(port=2000, debug=True)