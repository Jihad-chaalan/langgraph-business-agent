import csv
import os
from langgraph.graph import StateGraph, END
from typing import TypedDict
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()



# ------------------- Load Data from CSV -------------------
def load_accounts():
    accounts = {}
    path = os.path.join("csv", "accounts.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing required file: {path}")
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            accounts[row['account_name'].lower()] = int(row['balance'])
    return accounts

def load_customers_debt():
    customers = {}
    path = os.path.join("csv", "customers_debt.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing required file: {path}")
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            customers[row['customer_name']] = {
                "debt": int(row['debt']),
                "days_overdue": int(row['days_overdue'])
            }
    return customers

def load_inventory():
    inventory = {}
    path = os.path.join("csv", "inventory.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing required file: {path}")
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            inventory[row['item_name'].lower()] = {
                "minimum_quantity": int(row['minimum_quantity']),
                "current_quantity": int(row['current_quantity']),
                "supplier": row['supplier']
            }
    return inventory


# ACCOUNTS = {
#     "cash": 10000,
#     "account receivable": 20100,
#     "payroll": 1000000
# }

# CUSTOMERS_DEBT = {
#     "Ali" : { "debt": 1300, "days_overdue": 30 },
#     "Malik": { "debt": 700, "days_overdue": 90 },
#     "Fatima": { "debt": 500, "days_overdue": 45 }
# }

# INVENTORY = {
#     "laptops": {"minimum_quantity": 10, "current_quantity": 5, "supplier": "Qataranji"},
#     "keyboards": {"minimum_quantity": 30, "current_quantity": 45, "supplier": "Teck World"},
#     "monitors": {"minimum_quantity": 20, "current_quantity": 15, "supplier": "Tahhan+"},
# }

ACCOUNTS = load_accounts()
CUSTOMERS_DEBT = load_customers_debt()
INVENTORY = load_inventory()

# print(f"ACCOUNTS: {ACCOUNTS}")
# print('-'*50)
# print(f"CUSTOMERS_DEBT: {CUSTOMERS_DEBT}")
# print('-'*50)
# print(f"INVENTORY: {INVENTORY}")


#----------------- LLMS Declaration -----------------


def get_groq_llm():
    return ChatGroq(
        model="openai/gpt-oss-120b",  
        temperature=0,api_key=os.getenv("GROQ_API_KEY")
    )
llm = get_groq_llm()


#-------------------- State Definition -------------
class AgentState(TypedDict):
    query: str
    classification: str | None
    account_balance: int | None
    llm_assessment: str | None
    message: str | None
    inventory_quantity: dict | None
    final_answer: str | None


#--------------------- Create Graph Nodes ----------

# Node 1: @@@@@ Classify the User Query @@@@@

def classify_question(state: AgentState):
    prompt = f"""
    Classify this question strictly as either:
    - 'accounting'
    - 'inventory'
    Question: {state['query']}
    Answer with ONLY the label.
    """
    result = llm.invoke(prompt)
    label = result.content.strip().lower()
     # Remove any surrounding quotes (single or double)
    label = label.strip("'\"")
    
 # default fallback
    
    print(f"[DEBUG] Classification: '{label}'")  # helpful for debugging
    return {"classification": label}



@tool
def get_account_balance(query: str) -> str:
    """get account balance from user query"""
    for name in ACCOUNTS:
        if name in query:
            balance = ACCOUNTS[name]
            result = f"Account Name: {name}, Balance: {balance}"
            print(result) #Debug
            return result

    return None

# Node 2: @@@@@ Accounting - Lookup Account Balance @@@@@
def accounting_lookup(state: AgentState):
    query = state["query"].lower()

    # Bind the tool to the LLM
    llm_with_tools = llm.bind_tools([get_account_balance])

    prompt = f"""
    The user asks about an account balance. Use the available tool to get the balance.
    User query: {query}
    """

    response = llm_with_tools.invoke(prompt)

    # Check if the model requested a tool call
    if response.tool_calls:
        tool_call = response.tool_calls[0]
        if tool_call["name"] == "get_account_balance":

            tool_args = tool_call["args"]
            balance_result = get_account_balance.invoke(tool_args.get("query", query))
            if balance_result:
                return {"account_balance": balance_result}
            else:
                return {"account_balance": f"Account not found for '{query}'"}
    

    balance_result = get_account_balance.invoke(query)
    if balance_result:
        return {"account_balance": balance_result}
    else:
        return {"account_balance": f"Could not retrieve balance for '{query}'"}


# Node 3: @@@@@ Accounting - LLM Assessment Node @@@@@
def accounting_assessment(state: AgentState):
    balance = state["account_balance"]
    prompt = f"""
    The name and balance of a business account is: {balance}. 
    classify this accoung balance according to your best judgement 
    for a small business shop strictly as either:
    - 'low'
    - 'acceptable'
    Answer with ONLY the label
    """
    text = llm.invoke(prompt).content.strip().lower()
    print("LLM account assessment: ", text) ##Debug
    return {"llm_assessment": text}



@tool
def get_overdue_customer_debt() -> str:
    """Get the most overdue customer debt"""
    customer_name = ""
    max_overdue = 0
    debt = 0
    for name, data in CUSTOMERS_DEBT.items():
        if data["days_overdue"] > max_overdue:
            max_overdue = data["days_overdue"]
            customer_name = name
            debt = data["debt"]

    result = f"Customer: {customer_name} has debt amount: {debt} overdue for {max_overdue} days."
    print("Customer overdue Info: ", result) #################Debug
    return result

#Node 4: @@@@@ Accounting - Collect Debt from customer with highest overdue @@@@@
def collect_debt(state: AgentState):
    llm_assessment = state.get("llm_assessment")

    if llm_assessment is None:
        return {"message": "No suggestion"}
    
    if llm_assessment.lower().strip() == 'low':
        # Directly call the tool (no agent)
        debt_info = get_overdue_customer_debt.invoke("")
        
        # Use LLM to draft a friendly reminder email
        draft_prompt = f"""
        Based on this customer debt information: {debt_info}
        Write a short, polite email reminder asking the customer to pay as soon as possible.
        Keep it professional and friendly.
        """
        draft = llm.invoke(draft_prompt).content
        
        message = "**Recommendation to collect debt. Here is prepared draft to send to customer:**\n\n"
        return {"message": message + draft}
    else:
        return {"message": "No further action needed."}
    

    # Node 5: @@@@@ Accounting - Good standing Account @@@@@
def accounting_assessment_good(state: AgentState):
    balance = state["account_balance"]
    prompt = f"""
    Provide a concise and a very short assessment of two or three sentences ONLY about the following 
    account balance for a small retail business. The account name and balance is: {balance}. 
    Do you think the balance of this specific account is adequate for this specific account? 
    Answer very briefly.
    """
    text = llm.invoke(prompt).content
    return {"message": text}

# Node 6: %%%% Inventory Lookup Node %%%%
def inventory_lookup(state: AgentState):
    query = state["query"].lower()

    found_item = None
    for item in INVENTORY:
        if item in query:
            found_item = item
            break

    if found_item is None:
        return {"inventory_quantity": None}

    qty_data = INVENTORY[found_item]
    return {"inventory_quantity": qty_data}

# Node 7: %%%% Inventory - LLM Assessment Node %%%%
def inventory_assessment(state: AgentState):
    qty_info = state["inventory_quantity"]

    if qty_info is None:
        return {"llm_assessment": "Item not found."}

    prompt = f"""
    Current qty: {qty_info['current_quantity']}
    Minimum qty: {qty_info['minimum_quantity']}
    Provide advice on whether to restock and by how much. 
    Be brief and answer in three to four sentences ONLY.
    """
    text = llm.invoke(prompt).content
    return {"message": text}

# Node 8: &&&& Final Formatting Node &&&&
def format_response(state: AgentState):
    formatted = f"""
    QUERY: {state['query']}
    
    RESULT:
    {state['message']}
    """
    return {"final_answer": formatted}



# ---- --------- Build the Graph ---------------------
graph = StateGraph(AgentState)

# ---------------- Add nodes ----------------------
graph.add_node("node_classify", classify_question)
graph.add_node("node_account_lookup", accounting_lookup)
graph.add_node("node_account_assessment", accounting_assessment)
graph.add_node("node_collect_debt", collect_debt)
graph.add_node("node_account_good_standing", accounting_assessment_good)
graph.add_node("node_inventory_lookup", inventory_lookup)
graph.add_node("node_inventory_assessment", inventory_assessment)
graph.add_node("node_final_format", format_response)

# S------------------- Set Entry point ----------------------------
graph.set_entry_point("node_classify")

# -------------------- Create Edges to link Nodes ---------------------
# Conditional routing based on classification
def route(state: AgentState):
    return state["classification"]

graph.add_conditional_edges(
    "node_classify",                 # node
    route,                      # routing_function
    {                           # True : "node"
        "accounting": "node_account_lookup",
        "inventory": "node_inventory_lookup",
    }
)

# Accounting chain
graph.add_edge("node_account_lookup", "node_account_assessment")

def route2(state: AgentState):
    return state["llm_assessment"]

graph.add_conditional_edges(
    "node_account_assessment",                 # node
    route2,                      # routing_function
    {                           # True : "node"
        "low": "node_collect_debt",
        "acceptable": "node_account_good_standing",
    }
)

graph.add_edge("node_account_good_standing", "node_final_format")
graph.add_edge("node_collect_debt", "node_final_format")

# Inventory chain
graph.add_edge("node_inventory_lookup", "node_inventory_assessment")
graph.add_edge("node_inventory_assessment", "node_final_format")

#  ------------- Set End Node ---------------------
graph.add_edge("node_final_format", END)

# ------------- Compile Graph ---------------------
app = graph.compile()

# ----------------- Run Example -----------------------------
# Scenario 1: ask about Cash balance
print("#"*30)
result = app.invoke({"query": "What is the status of our cash balance?"})
print("\n=== RESPONSE 1 ===")
print(result["final_answer"])

# Scenario 2: ask about investment
print("#"*30)
result = app.invoke({"query": "check our payroll balance if adequet for a small shop?"})
print("\n=== RESPONSE 2 ===")
print(result["final_answer"])

# Scenario 3: ask about Inventory
print("#"*30)
result2 = app.invoke({"query": "Do we need to restock monitors?"})
print("\n=== RESPONSE 3 ===")
print(result2["final_answer"])

# Scenario 4: ask about Inventory
print("#"*30)
result2 = app.invoke({"query": "Do we need to restock keyboards?"})
print("\n=== RESPONSE 4 ===")
print(result2["final_answer"])
