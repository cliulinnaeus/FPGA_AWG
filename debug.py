def tokenize(prog_line):
    prog_line = prog_line.strip("[]").replace(" ", "")
    prog_line = iter(prog_line)
    in_loop = False
    curr_token = ""
    open_parenthesis = 0
    result = []
    for c in prog_line:
        if not in_loop:
            if c == ",":
                if curr_token != "":
                    result.append(curr_token)
                    curr_token = ""   
                # the case where it just come out of the loop
                else:
                    pass
            elif curr_token == "loop":
                # c must be "("
                result.append("loop")
                curr_token = ""
                in_loop = True
                open_parenthesis += 1
            else:
                curr_token += c
        else:
            # read loop count until the first "," in loop
            while c != ",":
                curr_token += c
                c = next(prog_line)
            result.append(curr_token)    # save loop count
            curr_token = ""
            # read until there are no open parenthesis, then we are out of the loop
            for c in prog_line:
                if c == "(":
                    open_parenthesis += 1
                elif c == ")":
                    open_parenthesis -= 1
                    
                if open_parenthesis > 0:
                    curr_token += c
                else:
                    result.append(curr_token)
                    curr_token = ""
                    in_loop = False
                    break
    return result
        
    
def is_loop_body(token):
    # checks if token is loop body, i.e. []
    return token.startswith('[') and token.endswith(']')


def list_all_pulses(tokens_set, tokens_lst):
    for t in tokens_lst:
        # loop body is not tokenize, so it needs to be further tokenized
        if is_loop_body(t):
            list_all_pulses(tokens_set, tokenize(t))
        else:
            # if t is a number, this means to wait, so don't save it in the set
            if not t.isnumeric() and t != "loop":
                tokens_set.update(t)
tokens = set()
tokens_lst = ['loop', '10', '[Dog,Cat,DOg,cat,DO,CA,DO,AC, cA]', 'CA']
list_all_pulses(tokens, tokens_lst)