import hashlib
import json
from textwrap import dedent
from time import time
from uuid import uuid4
from urllib.parse import urlparse

import requests 

from flask import Flask, jsonify, request

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        # Criação do block genesis - um bloco sem antecessores.
        self.new_block(previous_hash=1, proof=100)
    
    def register_node(self, address):
        """
        Adiciona um novo nódulo à lista de nódulos
        :paramêtro endereço (adress): Endereço do nódulo Eg. 'http://192.168.0.5:5000'
        :return: None

        Add a new node to the list of nodes
        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        :return: None
        """

        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')
    
    def valid_chain(self, chain):
        """
        Determina se a blockchain é válida
        :paramêtro corrente (chain): Uma blockchain
        :return: True se for válida, Falso se não.

        Determine if a given blockchain is valid
        :param chain: A blockchain
        :return: True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")

            # Check that the hash of the block is correct
            # Verificação de que o hash do bloco está correto
            last_block_hash = self.hash(last_block)
            if block['previous_hash'] != last_block_hash:
                return False

            # Check that the Proof of Work is correct
            # Verificação de que a prova de trabalho está correta
            if not self.valid_proof(last_block['proof'], block['proof'], last_block_hash):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        Esse é o algoritmo de consenso, ele resolve conflitos
        ao substituir na nossa corrent com a corrente mais longa da rede.
        :return: True se a corrente (chain) for substituída, False se não.

        This is our consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        # Aqui estamos buscando correntes mais longas que a nossa
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        # Busca e verificação de correntes de todos os nódulos da nossa rede.
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                # Verificar se o tamanho da corrente (chain) é o maior possível e se é válida
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        # Substituir nossa corrente (chain) caso descubramos uma nova corrente válida mais longa que a nossa
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof, previous_hash=None):
        """
        Criar um novo bloco na blockchain
        :param prova (proof): <int> a prova é dada pelo algoritmo de proof of work
        :param hash_anterior (previous_hash): <str> Hash do bloco anterior
        return: <dict> Novo bloco (new block)

        Create a new Block in the Blockchain
        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block
    
    def new_transaction(self, sender, recipient, amount):
        """
        Cria uma nova transação para o próximo bloco mineirado.
        :paramêtro remetente: <str> Endereço do remetente (sender)
        :paramêtro recebido: <str> Endereço recebido (recepient)
        :paramêtro quantidade: <int> Quantidade (amount)
        :return: <int> O index do bloco que irá assegurar essa transação

        Creates a new transaction to go into the next mined Block
        :param sender: <str> Address of the Sender
        :param recipient: <str> Address of the Recipient
        :param amount: <int> Amount
        :return: <int> The index of the Block that will hold this transaction
        """

        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1
    
    def proof_of_work(self, last_proof):
        """
        Algoritmo de prova de trabalho (Proof of Work):
         - Encontre um número p' tal que a hash(pp') contenha 4 zeros no início, onde p é o p' anterior.
         - p é a prova prévia e p' é a nova prova.
        :paramêtro last_proof: <int>
        :return: <int>
        
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeros, where p is the previous p'
         - p is the previous proof, and p' is the new proof
        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validação da prova: O hash(last_proof, proof) contem 4 zeros iniciais?
        
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"
    
    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Cria um hash SHA-256 de um bloco
        :paramêtro block: <dict> Block
        :return: <str>

        Creates a SHA-256 hash of a Block
        :param block: <dict> Block
        :return: <str>
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        # É preciso que tenhamos certeza que o dicionário está ordenado ou teremos hashes inconsistentes.
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

# Instantiate the node of the blockchain:
# Instanciando o flask:
app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# Generate a globally unique address for this node:
# Gerando globalmente um endereço único node:
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
# Instanciando a blockchain:
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    # Colocando o algoritmo de prova de trabalho (PoW) para conseguir a próxima prova...
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    # Devemos receber a recompensa por achar essa prova.
    # O remetente deve ser "0" para ressaltar que este nódulo mineirou uma nova moeda.

    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # Forge the new Block by adding it to the chain
    # Criação do novo bloco adicionando-o a "corrente" (chain)
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }

    return(jsonify(response), 200)

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json(force=True, silent=True, cache=False)  
    
    # Check that the required fields are in the POST'ed data
    # Verificação de que os campos requeridos estão corretos.
    required = ["sender", "recipient", "amount"]

    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    # Criação de uma nova transação
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
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
    app.run(host='0.0.0.0', port=5000)
