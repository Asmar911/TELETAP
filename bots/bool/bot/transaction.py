TRANSACTION_METHODS = {
    "eth_chainId":
        {
            "method": "eth_chainId",
            "params": [],
            "id": 1,
            "jsonrpc": "2.0"
        },
    "eth_getBalance":
        {
            "method": "eth_getBalance",
            "params": ['wallet_address', "latest"],
            "id": 1,
            "jsonrpc": "2.0"
        },
    "eth_blockNumber":
        {
            "method": "eth_blockNumber",
            "params": [],
            "id": 1,
            "jsonrpc": "2.0"
        },
    "eth_sendRawTransaction":
        {
            "method": "eth_sendRawTransaction",
            "params": ['transaction_hash'],
            "id": 1,
            "jsonrpc": "2.0"
        },
    "eth_getTransactionReceipt":
        {
            "method": "eth_getTransactionReceipt",
            "params": ['transaction_hash'],
            "id": 1,
            "jsonrpc": "2.0"
        },
    "eth_getTransactionCount":
        {
            "method": "eth_getTransactionCount",
            "params": ['wallet_address', "latest"],
            "id": 1,
            "jsonrpc": "2.0"
        },
    "eth_getTransactionByHash":
        {
            "method": "eth_getTransactionByHash",
            "params": ['transaction_hash'],
            "id": 1,
            "jsonrpc": "2.0"
        },
    "eth_getBlockByNumber":
        {
            "method": "eth_getBlockByNumber",
            "params": ['block_number', True],
            "id": 1,
            "jsonrpc": "2.0"
        }
}