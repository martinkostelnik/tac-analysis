import xml.etree.ElementTree as ET
import sys
import re

####################### DATA #######################
src_file = sys.stdin                # Source file containing XML

stats = {'enabled': False,
         'path': '',
         'order': [],
         '--insts': 0,
         '--vars': 0}

PC = 1                              # Program counter
TF = {'exists': False, 'frame': {}} # Temporary frame
LF_stack = []                       # Local frame stack
GF = {}                             # Global frame
data_stack = []                     # Data stack
call_stack = []                     # Function call stack
labels = []                         # Labels
####################################################
##################### CLASSES ######################
class Operand:
    def __init__(self, type, value, order):
        self.type = type
        self.value = value
        self.order = order

class Instruction:
    def __init__(self, opcode, order, operands):
        self.opcode = opcode
        self.order = int(order)
        self.operands = operands

    def interpret(self):
        global PC

        switch = {
            'MOVE':         i_move,
            'CREATEFRAME':  i_createframe,
            'PUSHFRAME':    i_pushframe,
            'POPFRAME':     i_popframe,
            'DEFVAR':       i_defvar,
            'CALL':         i_call,
            'RETURN':       i_return,
            'PUSHS':        i_pushs,
            'POPS':         i_pops,
            'ADD':          i_add,
            'SUB':          i_sub,
            'MUL':          i_mul,
            'IDIV':         i_idiv,
            'LT':           i_lt,
            'GT':           i_gt,
            'EQ':           i_eq,
            'AND':          i_and,
            'OR':           i_or,
            'NOT':          i_not,
            'INT2CHAR':     i_int2char,
            'STRI2INT':     i_stri2int,
            'READ':         i_read,
            'WRITE':        i_write,
            'CONCAT':       i_concat,
            'STRLEN':       i_strlen,
            'GETCHAR':      i_getchar,
            'SETCHAR':      i_setchar,
            'TYPE':         i_type,
            'LABEL':        i_label,
            'JUMP':         i_jump,
            'JUMPIFEQ':     i_jumpifeq,
            'JUMPIFNEQ':    i_jumpifneq,
            'EXIT':         i_exit,
            'DPRINT':       i_dprint,
            'BREAK':        i_break
        }

        try:
            switch[self.opcode](self.operands)
        except KeyError:
            abort(32, "unknown operation code")

        PC += 1
####################################################
################### PRE-INTERPRET ##################
def parse_args():
    global src_file, stats

    if len(sys.argv) < 2:
        abort(10, "invalid aguments")

    if "-h" in sys.argv or "--help" in sys.argv:
        if len(sys.argv) != 2:
            abort(10, "-h/--help cannot be combined with other arguments")
        else:
            print("Program nacte XML reprezentaci programu a tento program s vyuzitim vstupu dle parametru prikazove radky interpretuje a generuje vystup. Vstupni XML reprezentace je napr. generovana skriptem parse.php (ale ne nutne) ze zdrojoveho kodu v IPPcode20.")
            sys.exit(0)

    filesOK = False
    for arg in sys.argv:
        if arg[0 : 9] == "--source=":
            src_file = arg[9:]
            filesOK = True

        elif arg[0 : 8] == "--input=":
            try:
                sys.stdin = open(arg[8:])
            except FileNotFoundError:
                abort(11, "could not open input file")

            filesOK = True

        elif arg[0 : 8] == "--stats=":
            stats['path'] = arg[8:]
            stats['enabled'] = True

    for arg in sys.argv:
        if arg == "--vars" or arg == "--insts":
            if not stats['enabled']:
                abort(10, "--insts or --var cannot be used without --stats argument")

            stats['order'].append(arg)

    if not filesOK:
        abort(10, "you must specify --source argument, --input argument or both")

    #TODO: Unknown arguments

def read_code():
    instructions = []

    try:
        tree = ET.parse(src_file)
    except ET.ParseError:
        abort(31, "XML not well formed")
    except FileNotFoundError:
        abort(11, "unable to open XML file")

    root = tree.getroot()

    if root.tag != "program":
        abort(32, "incorrect program tag")

    for i in root:
        operands = []

        if i.tag != "instruction":
            abort(32, "incorrect instruction tag")

        for operand in i:
            if operand.tag not in ["arg1", "arg2", "arg3"]:
                abort(32, "incorrect operand tag")
            
            try:
                operand_order = int(operand.tag[3:])
            except ValueError:
                abort(32, "incorrect operand order value")

            if operand_order > len(i):
                abort(32, "incorrect operand order")

            operands.append(Operand(operand.attrib['type'], operand.text, operand_order))
            operands.sort(key = lambda x: x.order)

        try:
            instructions.append(Instruction(i.attrib['opcode'], int(i.attrib['order']) if (int(i.attrib['order']) > 0) else abort(32, "invalid order"), operands))
        except KeyError:
            abort(32, "missing opcode or order attribute")
        except ValueError:
            abort(32, "Invalid order value")

    instructions.sort(key = lambda x: x.order, reverse = False)
    normalize_order(instructions)
    return instructions

def scan_labels(instructions):
    global labels

    for i in instructions:
        if i.opcode == "LABEL":
            if i.operands[0].type != "label":
                abort(53, "incorrect label operand type")

            if any(label['name'] == i.operands[0].value for label in labels):
                abort(52, "label redefinition")

            labels.append({'name': i.operands[0].value, 'index': i.order})
####################################################    
##################### HELPERS ######################
def abort(code, message):
    global PC

    sys.stderr.write("ERROR at (" + str(PC) + ") : " + message + "\n")
    sys.exit(code)

def normalize_order(code):
    i = 0
    for instr in code:
        instr.order = i
        i += 1

# Returns true and <value> if frame is ok AND variable exists in said frame
# Returns false if frame is ok AND variable does not exist in said frame
# Aborts if frame is not ok OR type is not var
def check_var(operand):
    global TF, LF_stack, GF

    if operand.type != "var":
        abort(53, "incorrect operand type")

    frame = operand.value[0 : 2]
    name = operand.value[3 : ]

    if frame == "TF":
        if not TF['exists']:
            abort(55, "TF does not exist, use CREATEFRAME first")

        if name in TF['frame'].keys():
            return True, TF['frame'][name]
        else:
            return False, None
    elif frame == "GF":
        if name in GF.keys():
            return True, GF[name]
        else:
            return False, None
    elif frame == "LF":
        if not LF_stack:
            abort(55, "no local frame exists")
    
        if name in LF_stack[-1].keys():
            return True, LF_stack[-1][name]
        else:
            return False, None

def esc_replace(match):
    match = match.group()
    return chr(int(match[1:]))

# Returns value of variable
# Returns string value
# Returns bool value
# Returns int value
# Returns None if type is nil
# Aborts if variable does not exist OR type is not ok OR variable is undefined
def get_symb_value(operand):
    if operand.type == "var":
        exists, value = check_var(operand)

        if exists:
            if value == [0]:
                abort(56, "reading from undefined variable")

            return value
        else: # variable does not exist
            abort(54, "variable does not exist")
    elif operand.type == "string":
        if not operand.value:
            return ""
        
        pattern = re.compile(r"\\\d{3}")
        string = re.sub(pattern, esc_replace, str(operand.value))
        return string
    elif operand.type == "bool":
        return True if operand.value == "true" else False
    elif operand.type == "int":
            try:
                return int(operand.value)
            except ValueError:
                abort(32, "invalid int")
    elif operand.type == "nil":
        return None
    else:
        abort(53, "incorrect operand type")

def assign(frame, var_name, value):
    global GF, LF_stack, TF
    
    if frame == "GF":
        GF[var_name] = value
    elif frame == "LF":
        LF_stack[-1][var_name] = value
    elif frame == "TF":
        TF['frame'][var_name] = value

# Returns  0 if lval == rval
# Returns  1 if lval > rval
# Returns -1 if lval < rval
def compare(lval, rval):
    if (type(lval) is int and type(rval) is int) or (type(lval) is str and type(rval) is str) or (type(lval) is bool and type(rval) is bool):
        if lval == rval:
            return 0
        elif lval > rval:
            return 1
        else:
            return -1
    else:
        abort(53, "incorrect operand type")

####################################################
################### INSTRUCTIONS ###################

# <existing var> <existing defined var OR constant>
def i_move(operands):
    target_exists, _ = check_var(operands[0])
    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]

    source_value = get_symb_value(operands[1])

    if target_exists:
        assign(target_frame, target_name, source_value)
    else:
        abort(54, "variable does not exist")

def i_createframe(operands):
    global TF

    TF['exists'] = True
    TF['frame'] = {}

def i_pushframe(operands):
    global TF, LF_stack

    if not TF['exists']:
        abort(55, "TF not created, use CREATEFRAME first")

    LF_stack.append(TF['frame'])
    TF['exists'] = False
    TF['frame'] = {}

def i_popframe(operands):
    global TF, LF_stack

    if not LF_stack:
        abort(55, "LF stack is empty, cannot pop")

    TF['exists'] = True
    TF['frame'] = LF_stack.pop()

# <nonexising var>
def i_defvar(operands):
    var_exists, _ = check_var(operands[0])
    var_frame = operands[0].value[0 : 2]
    var_name = operands[0].value[3 : ]

    if var_exists:
        abort(52, "variable already exists in " + str(var_frame) + " ")
    else:
        assign(var_frame, var_name, [0])

# <existing label>
def i_call(operands):
    global PC, labels, call_stack

    if operands[0].type != "label":
        abort(53, "incorrect operand type")

    call_stack.append(PC)
    i_jump(operands)

def i_return(operands):
    global PC, call_stack

    if not call_stack:
        abort(56, "call_stack is empty, cannot pop")

    PC = call_stack.pop()

# <existing defined var OR constant>
def i_pushs(operands):
    global data_stack

    data_stack.append(get_symb_value(operands[0]))

# <existing var>
def i_pops(operands):
    global data_stack

    var_exists, _ = check_var(operands[0])
    var_frame = operands[0].value[0 : 2]
    var_name = operands[0].value[3 : ]

    if data_stack:
        if var_exists:
            assign(var_frame, var_name, data_stack.pop())
        else:
            abort(54, "variable does not exist in " + str(var_frame))
    else:
        abort(56, "data stack is empty, cannot pop")

# <existing var> <existing defined int var OR int constant> <existing defined int var OR int constant>
def i_add(operands):
    target_exists, _ = check_var(operands[0])
    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]

    lval = get_symb_value(operands[1])
    rval = get_symb_value(operands[2])

    if target_exists:
        if operands[1].type not in ["int", "var"] or operands[2].type not in ["int", "var"]:
            abort(53, "incorrect operand type")

        try:
            value = int(lval) + int(rval)
        except (ValueError, TypeError) as e:
            abort(53, "can only add integers")

        assign(target_frame, target_name, value)
    else:
        abort(54, "variable does not exist")

# <existing var> <existing defined int var OR int constant> <existing defined int var OR int constant>
def i_sub(operands):
    target_exists, _ = check_var(operands[0])
    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]

    lval = get_symb_value(operands[1])
    rval = get_symb_value(operands[2])
  
    if target_exists:
        if operands[1].type not in ["int", "var"] or operands[2].type not in ["int", "var"]:
            abort(53, "incorrect operand type")
        try:
            value = int(lval) - int(rval)
        except (ValueError, TypeError) as e:
            abort(53, "can only subtract integers")

        assign(target_frame, target_name, value)
    else:
        abort(54, "variable does not exist")

# <existing var> <existing defined int var OR int constant> <existing defined int var OR int constant>
def i_mul(operands):
    target_exists, _ = check_var(operands[0])
    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]

    lval = get_symb_value(operands[1])
    rval = get_symb_value(operands[2])
    
    if target_exists:
        if operands[1].type not in ["int", "var"] or operands[2].type not in ["int", "var"]:
            abort(53, "incorrect operand type")

        try:
            value = int(lval) * int(rval)
        except (ValueError, TypeError) as e:
            abort(53, "can only multiply integers")

        assign(target_frame, target_name, value)
    else:
        abort(54, "variable does not exist")

# <existing var> <existing defined int var OR int constant> <existing defined int var OR int constant>
def i_idiv(operands):
    target_exists, _ = check_var(operands[0])
    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]

    lval = get_symb_value(operands[1])
    rval = get_symb_value(operands[2])
    
    if target_exists:
        if operands[1].type not in ["int", "var"] or operands[2].type not in ["int", "var"]:
            abort(53, "incorrect operand type")

        try:
            value = int(lval) // int(rval)
        except (ValueError, TypeError) as e:
            abort(53, "can only divide integers")
        except ZeroDivisionError:
            abort(57, "cannot divide by zero")

        assign(target_frame, target_name, value)
    else:
        abort(54, "variable does not exist")

# <existing var> <existing defined not nil var OR not nil constant> <existing defined not nil var OR not nil constant> same type
def i_lt(operands):
    target_exists, _ = check_var(operands[0])
    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]

    lval = get_symb_value(operands[1])
    rval = get_symb_value(operands[2])

    if target_exists:
        if compare(lval, rval) == -1:
            assign(target_frame, target_name, True)
        else:
            assign(target_frame, target_name, False)
    else:
        abort(54, "variable does not exist")

# <existing var> <existing defined not nil var OR not nil constant> <existing defined not nil var OR not nil constant> same type
def i_gt(operands):
    target_exists, _ = check_var(operands[0])
    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]

    lval = get_symb_value(operands[1])
    rval = get_symb_value(operands[2])

    if target_exists:
        if compare(lval, rval) == 1:
            assign(target_frame, target_name, True)
        else:
            assign(target_frame, target_name, False)
    else:
        abort(54, "variable does not exist")

# <existing var> <existing defined not nil var OR not nil constant> <existing defined not nil var OR not nil constant> same type
def i_eq(operands):
    target_exists, _ = check_var(operands[0])
    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]

    lval = get_symb_value(operands[1])
    rval = get_symb_value(operands[2])

    if target_exists:
        if lval == None or rval == None:
            if lval == None and rval == None:
                assign(target_frame, target_name, True)
            else:
                assign(target_frame, target_name, False)
            return

        if compare(lval, rval) == 0:
            assign(target_frame, target_name, True)
        else:
            assign(target_frame, target_name, False)
    else:
        abort(54, "variable does not exist")

# <existing var> <existing defined bool var OR bool constant> <existing defined bool var OR bool constant>
def i_and(operands):
    target_exists, _ = check_var(operands[0])
    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]

    lval = get_symb_value(operands[1])
    rval = get_symb_value(operands[2])

    if target_exists:
        if operands[1].type not in ["bool", "var"] or operands[2].type not in ["bool", "var"]:
            abort(53, "incorrect operand type")
    
        assign(target_frame, target_name, lval and rval)
    else:
        abort(54, "variable does not exist")

# <existing var> <existing defined bool var OR bool constant> <existing defined bool var OR bool constant>
def i_or(operands):
    target_exists, _ = check_var(operands[0])
    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]

    lval = get_symb_value(operands[1])
    rval = get_symb_value(operands[2])

    if target_exists:
        if operands[1].type not in ["bool", "var"] or operands[2].type not in ["bool", "var"]:
            abort(53, "incorrect operand type")

        assign(target_frame, target_name, lval or rval)
    else:
        abort(54, "variable does not exist")

# <existing var> <existing defined bool var OR bool constant>
def i_not(operands):
    target_exists, _ = check_var(operands[0])
    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]

    value = get_symb_value(operands[1])

    if target_exists:
        if operands[1].type not in ["bool", "var"]:
            abort(53, "incorrect operand type")

        if operands[1].type == "var" and type(value) is not bool:
            abort(53, "incorrect operand type")
        
        try:
            assign(target_frame, target_name, not bool(value))
        except (ValueError, TypeError) as e:
            abort(53, "incorrect operand type")
    else:
        abort(54, "variable does not exist")

# <existing var> <existing defined int var OR int constant>
def i_int2char(operands):
    target_exists, _ = check_var(operands[0])
    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]

    value = get_symb_value(operands[1])

    if target_exists:
        if operands[1].type not in ["int", "var"] or type(value) is not int:
            abort(53, "incorrect operand type")

        try:
            assign(target_frame, target_name, chr(value))
        except ValueError:
            abort(58, "value out of UNICODE range")
        except TypeError:
            abort(53, "incorrect operand type")
    else:
        abort(54, "variable does not exist")

# <existing var> <existing defined string var OR string constant> <existing defined int var OR int constant>
def i_stri2int(operands):
    target_exists, _ = check_var(operands[0])
    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]

    string = get_symb_value(operands[1]) #string only
    index = get_symb_value(operands[2])  #int only

    if target_exists:
        if operands[1].type not in ["string", "var"] or operands[2].type not in ["int", "var"]:
            abort(53, "incorrect operand type")

        if index >= len(string) or index < 0:
            abort(58, "index out of range")
        if not string:
            abort(58, "string is empty")

        assign(target_frame, target_name, ord(string[index]))
    else:
        abort(54, "variable does not exist")

# <existing var> <type>
def i_read(operands):
    target_exists, _ = check_var(operands[0])
    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]
   
    if operands[1].type == "type":
        operand_type = operands[1].value
    else:
        abort(32, "Incorrect type")
    
    if target_exists:

        try:
            value = input()
        except EOFError:
            assign(target_frame, target_name, None)
            return

        if operand_type == "string":
            assign(target_frame, target_name, str(value))
            return
        elif operand_type == "bool":
            if value.lower() == "true":
                assign(target_frame, target_name, True)
                return
            else:
                assign(target_frame, target_name, False)
                return
        elif operand_type == "int":
            try:
                assign(target_frame, target_name, int(value))
                return
            except (ValueError, TypeError) as e:
                assign(target_frame, target_name, None)
                return
        else:
            abort(57, "invalid type value")
    else:
        abort(54, "variable does not exist")

# <existing defined var OR constant>
def i_write(operands):
    value = get_symb_value(operands[0])

    if value == None:
        print("", end = '')
    elif type(value) == bool:
        if value:
            print("true", end = '')
        else:
            print("false", end = '')
    else:
        print(str(value), end = '')

# <existing var> <existing defined string var OR string constant> <existing defined string var OR string constant> 
def i_concat(operands):
    var_exists, _ = check_var(operands[0])
    var_frame = operands[0].value[0 : 2]
    var_name = operands[0].value[3 : ]

    lval = get_symb_value(operands[1])
    rval = get_symb_value(operands[2])
    
    if var_exists:
        if type(lval) != str or type(rval) != str:
            abort(53, "incorrect operand type")

        value = lval + rval

        assign(var_frame, var_name, value)
    else:
        abort(54, "variable does not exist")

# <existing var> <existing defined string var OR string constant>
def i_strlen(operands):
    var_exists, _ = check_var(operands[0])
    var_frame = operands[0].value[0 : 2]
    var_name = operands[0].value[3 : ]

    value = get_symb_value(operands[1])
    
    if var_exists:
        if type(value) != str:
            abort(53, "incorrect operand type")

        assign(var_frame, var_name, len(value))
    else:
        abort(54, "variable does not exist")

# <existing var> <existing defined string var OR string constant> <existing defined int var OR int constant>
def i_getchar(operands):
    target_exists, _ = check_var(operands[0])
    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]

    string = get_symb_value(operands[1])
    index = get_symb_value(operands[2])

    if target_exists:
        if operands[1].type not in ["string", "var"] or operands[2].type not in ["int", "var"]:
            abort(53, "incorrect operand type")

        if index >= len(string) or index < 0:
            abort(58, "index out of range")

        assign(target_frame, target_name, str(string[index]))
    else:
        abort(54, "variable does not exist")

# <existing defined string var> <existing defined int var OR int constant> <existing defined string var OR string constant>
def i_setchar(operands):
    target_exists, value = check_var(operands[0])

    if value == [0]:
        abort(56, "reading from undefined variable")

    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]

    index = get_symb_value(operands[1])
    string = get_symb_value(operands[2])

    if target_exists:
        if operands[1].type not in ["int", "var"] or operands[2].type not in ["string", "var"] or type(value) is not str:
            abort(53, "incorrect operand type")

        if index >= len(value) or index < 0:
            abort(58, "index out of range")
        if not string:
            abort(58, "empty string")
        
        try:
            value = list(value)
            value[index] = string[0]
            value = "".join(value)
        except TypeError:
            abort(53, "incorrect operand type")

        assign(target_frame, target_name, value)
    else:
        abort(54, "variable does not exist")

# <existing var> <any var OR constant>
def i_type(operands):
    target_exists, value = check_var(operands[0])
    target_frame = operands[0].value[0 : 2]
    target_name = operands[0].value[3 : ]

    if target_exists:
        if operands[1].type == "var":
            e, v = check_var(operands[1])
            if e and v == [0]:
                assign(target_frame, target_name, "")
                return
        
        value = get_symb_value(operands[1])

        if value == None:
            assign(target_frame, target_name, "nil")
        elif type(value) == str:
            assign(target_frame, target_name, "string")
        elif type(value) == int:
            assign(target_frame, target_name, "int")
        elif type(value) == bool:
            assign(target_frame, target_name, "bool") 
    else:
        abort(54, "variable does not exist")

def i_label(operands):
    return

# <existing label>
def i_jump(operands):
    global labels, PC

    if operands[0].type != "label":
        abort(53, "incorrect operand type")

    found = False

    for l in labels:
        if l['name'] == operands[0].value:
            PC = l['index']
            found = True
            break

    if not found:
        abort(52, "label not found")

def i_jumpifeq(operands):
    global labels, PC

    if operands[0].type != "label":
        abort(53, "incorrect operand type")

    found = False

    for l in labels:
        if l['name'] == operands[0].value:
            lval = get_symb_value(operands[1])
            rval = get_symb_value(operands[2])

            if lval == None or rval == None:
                if lval == None and rval == None:
                    i_jump(operands)
                    return
                else:
                    return

            if compare(lval, rval) == 0:
                i_jump(operands)
                return
            else:
                return
            
            found = True
            break

    if not found:
        abort(52, "label not found")

def i_jumpifneq(operands):
    global labels, PC

    if operands[0].type != "label":
        abort(53, "incorrect operand type")

    found = False

    for l in labels:
        if l['name'] == operands[0].value:
            lval = get_symb_value(operands[1])
            rval = get_symb_value(operands[2])

            if lval == None or rval == None:
                if (lval is None and rval is not None) or (lval is not None and rval is None):
                    i_jump(operands)
                    return
                else:
                    return

            if compare(lval, rval) != 0:
                i_jump(operands)
                return
            else:
                return
            
            found = True
            break

    if not found:
        abort(52, "label not found")

# <existing defined int var OR int constant>
def i_exit(operands):
    value = get_symb_value(operands[0])

    if type(value) != int:
        abort(53, "incorrect operand type")
    if value < 0 or value > 49:
        abort(57, "value out of range")

    sys.exit(value)

def i_dprint(operands):
    sys.stderr.write(str(get_symb_value(operands[0])) + "\n")

def i_break(operands):
    global PC, TF, GF, LF_stack

    sys.stderr.write("Program counter: " + str(PC) + "\n\n")
    sys.stderr.write("Temporary frame:\n" + str(TF) + "\n\n")
    sys.stderr.write("Global frame:\n" + str(GF) + "\n\n")

    sys.stderr.write("Local frames:\n")

    if LF_stack:
        for f in reversed(LF_stack):
            sys.stderr.write(str(f) + "\n")
    else:
        sys.stderr.write("[]\n")
####################################################

if __name__ == "__main__":
    parse_args()
    instructions = read_code()

    scan_labels(instructions)

    while (PC - 1) != len(instructions):
        instructions[PC - 1].interpret()
        