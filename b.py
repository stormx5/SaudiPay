import hashlib
import json
import os
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request

from pywallet import wallet


max_coin = 1000000000  # 1 Billion SART
Genisis_wallet_address = '834a32c74c0342039bf90e63a2e66829'
remaining_coin = 1000000000
#Genisis_flag = 0

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        #self.remaining_coin = 0
        # Create the genesis block
        self.new_block(previous_hash=1)
        #self.GenBlockAddMoney(Genisis_wallet_address,max_coin)
        self.nodes = set()

    def new_block(self, previous_hash=None):

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_transactions = []
 
        self.chain.append(block)
        return block

    def GenBlockAddMoney(self, gen_address, maxcoin):
        Genblock = {
            'sender' : '0',
            'recipient' : gen_address,
            'amount' : maxcoin,
        }

        self.chain.append(Genblock)

        return 'Genisis Block is ready'

    #get balance of a given address 
    def get_balance(self, AddressB):
        if AddressB == Genisis_wallet_address:
            global remaining_coin
            return remaining_coin
        else:
            balance_c = 0
            #print(AddressB)
            for blocks in self.chain:
                for Trans in blocks['transactions']:
                    if Trans['sender'] == AddressB:
                        balance_c -= Trans['amount']
                    if Trans['recipient'] == AddressB:
                        balance_c += Trans['amount']
            return balance_c
        


    def new_transaction(self, sender, recipient, amount):
               

        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1


    def proof_of_work(self, last_proof):
    
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof


    def register_node(self, address):
        
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print('{last_block}')
            print('{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def getChainIndex(self):
        print(self.chain.count)
        return self.chain.count



    def resolve_conflicts(self):
        
        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get('http://{node}/chain')

            if response.status_code == 200:
                json_data = response.json()
                length = json_data['length']
                chain = json_data['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def valid_proof(last_proof, proof):
        guess = '{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    @staticmethod
    def hash(block):

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()


# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()


#@app.route('/mine', methods=['GET'])
#def mine():
    # We run the proof of work algorithm to get the next proof...
#    last_block = blockchain.last_block
#    last_proof = last_block['proof']
#    proof = blockchain.proof_of_work(last_proof)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
#    blockchain.new_transaction(
#        sender="0",
#        recipient=node_identifier,
#        amount=1,
#    )

    # Forge the new Block by adding it to the chain
#    block = blockchain.new_block()

#    response = {
#        'message': "New Block Generated",
#        'index': block['index'],
#        'transactions': block['transactions'],
#        'previous_hash': block['previous_hash'],
#    }
#    return jsonify(response), 200

@app.route('/GetBalance', methods=['POST'])
def get_wallet_balance():
    Waddress = request.get_json(force=True)
    required = ['address']
    response = blockchain.get_balance(Waddress['address'])
    return jsonify(response), 200


@app.route('/CreateWallet', methods=['GET'])
def gen_wallet():
    seed = wallet.generate_mnemonic()
    w = wallet.create_wallet(network="BTC", seed=seed, children=1)
    return jsonify(w), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():

    values = request.get_json(force=True)
    #values = request._get_current_object()
    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400
    if values['sender'] == values['recipient']:
        return 'Recipient Address cannot match the sender address', 400


    #Check if Sender has enough Balance to send
    sender_address = values['sender']
    balance_check = blockchain.get_balance(sender_address)
    global remaining_coin
    if values['sender'] == Genisis_wallet_address and remaining_coin > values['amount']:
        remaining_coin = remaining_coin - values['amount']
    elif balance_check < values['amount']:
        return 'Balance is not enough to complete this transation', 400

    # Create a new Transaction 
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    block = blockchain.new_block()

    response = {
        'message': "New Block Generated",
        'index': block['index'],
        'transactions': block['transactions'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/chain', methods=['GET'])
def full_chain():
    #if blockchain.getChainIndex() <= 1:
        #GenBlockAddMoney(Genisis_wallet_address,max_coin)
    #blockchain.getChainIndex()
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 1234)))