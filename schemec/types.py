from collections import namedtuple


################################################################################
## Scheme Expressions
################################################################################

# VarExp = namedtuple('VarExp', 'name')
# LamExp = namedtuple('LamExp', 'vars, bodyExp')
# AppExp = namedtuple('AppExp', 'funcExp, argExps')
# IfExp  = namedtuple('IfExp',  'condExp, thenExp, elseExp')

## Atomic Expressions
class AtomicExp: pass

class VarExp(AtomicExp):
    """A variable.

    @type name: String
    @param name: The name of the variable
    """
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return str(self.name)

class NumExp(AtomicExp):
    """A number.

    @type val: Number
    @param val: The value
    """
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        return str(self.val)

class BoolExp(AtomicExp):
    """A boolean.

    @type val: Bool
    @param val: The value
    """
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        return "#t" if self.val else "#f"

class StrExp(AtomicExp):
    """A string.

    @type val: String
    @param val: The value
    """
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        return '"{0}"'.format(self.val)

class LamExp(AtomicExp):
    """A lambda expression.

    @type vars: A List of VarExps
    @param vars: The formal parameters of the lambda
    @type bodyExp: Any Scheme expression
    @param bodyExp: The body of the lambda
    """
    def __init__(self, vars, bodyExp):
        self.vars = vars
        self.bodyExp = bodyExp

    def __repr__(self):
        return '(lambda ({0}) {1})'.format(' '.join(map(str, self.vars)),
                                           self.bodyExp)


## More complex expressions
class AppExp:
    """A lambda application.

    @type funcExp: Any Scheme expression
    @param funcExp: The function being applied
    @type argExps: A List of Scheme Expressions (not passed as a list though!)
    @param argExps: The arguments to the function
    """
    def __init__(self, funcExp, *argExps):
        self.funcExp = funcExp
        self.argExps = argExps

    def __repr__(self):
        return '({0} {1})'.format(self.funcExp,
                                  ' '.join(map(str, self.argExps)))

class IfExp:
    """An if expression.

    All three parameters can be any Scheme expression.
    """
    def __init__(self, condExp, thenExp, elseExp):
        self.condExp = condExp
        self.thenExp = thenExp
        self.elseExp = elseExp

    def __repr__(self):
        return '(if {0} {1} {2})'.format(self.condExp, self.thenExp,
                                         self.elseExp)

class LetRecExp:
    """A letrec expression.

    @type varExp: A VarExp
    @param varExp: The symbol to which the function will be bound
    @type funcExp: A LamExp
    @param funcExp: The recursive function
    @type bodyExp: Any Scheme expression
    @param bodyExp: The body of the LetRec expression
    """
    def __init__(self, varExp, funcExp, bodyExp):
        self.varExp = varExp
        self.funcExp = funcExp
        self.bodyExp = bodyExp

    def __repr__(self):
        return '(letrec (({0} {1})) {2})'.format(self.varExp, self.funcExp,
                                                 self.bodyExp)

class BeginExp:
    """A begin expression.

    @type exps: A list of Scheme expressions
    @param exps: The expressions contained within the `begin`
    """
    def __init__(self, exps):
        self.exps = exps

    def __repr__(self):
        return '(begin {0})'.format(' '.join(self.exps))

################################################################################
## Conversion to CPS
################################################################################

class GenSym:
    n = 1
    def __call__(self, sym):
        sym += str(self.n)
        self.n += 1
        return VarExp(sym)
gensym = GenSym()

def T_k(exp, k):
    """Transform an expression into CPS with a continuation lifted into the host
    language.

    @type exp: A Scheme expression
    @param exp: The expression to transform
    @type k: A *Python* function from SchemeExp -> SchemeExp
    @param k: The continuation to apply
    """
    if isinstance(exp, AtomicExp):
        return k(M(exp))
    elif isinstance(exp, AppExp):
        _rv = gensym('$rv')
        cont = LamExp([_rv], k(_rv))
        return T_c(exp, cont)
    elif isinstance(exp, IfExp):
        ce = exp.condExp
        te = exp.thenExp
        ee = exp.elseExp
        return T_k(ce, lambda _ce: IfExp(_ce, T_k(te, k), T_k(ee, k)))
    elif isinstance(exp, LetRecExp):
        ve = exp.varExp
        fe = exp.funcExp
        be = exp.bodyExp
        return LetRecExp(ve, M(fe), T_k(be, k))
    else:
        raise TypeError(exp)

def T_c(exp, c):
    """Transform an expression into CPS.

    @type exp: A Scheme expression
    @param exp: The expression to transform
    @type c: LamExp
    @param c: The continuation to apply
    """
    if isinstance(exp, AtomicExp):
        return AppExp(c, M(exp))
    elif isinstance(exp, AppExp):
        f = exp.funcExp
        es = exp.argExps
        return T_k(f, lambda _f:
                   Tx_k(es, lambda _es:
                        AppExp(_f, *(_es + [c]))))
    elif isinstance(exp, IfExp):
        ce = exp.condExp
        te = exp.thenExp
        ee = exp.elseExp
        _k = gensym('$k')
        return AppExp(LamExp([_k], T_k(ce, lambda _ce:
                                       IfExp(_ce, T_c(te, _k), T_c(ee, _k)))),
                             c)
    elif isinstance(exp, LetRecExp):
        ve = exp.varExp
        fe = exp.funcExp
        be = exp.bodyExp
        return LetRecExp(ve, M(fe), T_c(be, c))
    else:
        raise TypeError(exp)

def Tx_k(exps, k):
    """Transform a list of expressions into CPS.

    @type exps: A List of SchemeExps
    @type k: LamExp
    """
    if len(exps) == 0:
        return k([])
    else:
        return T_k(exps[0],
                   lambda hd: Tx_k(exps[1:],
                                   lambda tl: k([hd] + tl)))

def M(exp):
    """Transform an AtomicExp into CPS.

    @type exp: AtomicExp
    """
    if isinstance(exp, LamExp):
        vars = exp.vars
        body = exp.bodyExp
        _k = gensym('$k')
        return LamExp(vars + [_k],
                      T_c(body, _k))
    elif isinstance(exp, AtomicExp):
        return exp
    else:
        raise TypeError(exp)


################################################################################
## Main
################################################################################

if __name__ == '__main__':
    exp = AppExp(LamExp([VarExp('g'), VarExp('h')], VarExp('g')),
                 BoolExp(True),
                 BoolExp(False))
    print(exp)
    print(T_c(exp, VarExp('halt')))

    exp = IfExp(IfExp(BoolExp(True), BoolExp(False), BoolExp(True)), NumExp(1), NumExp(0))
    print(exp)
    print(T_c(exp, VarExp('halt')))

    exp = LetRecExp(VarExp('fact'), LamExp([VarExp('x')],
                                           IfExp(AppExp(VarExp('='),
                                                        VarExp('x'),
                                                        NumExp(0)),
                                                 NumExp(1),
                                                 AppExp(VarExp('*'),
                                                        VarExp('x'),
                                                        AppExp(VarExp('fact'),
                                                               AppExp(VarExp('-'),
                                                                      VarExp('x'),
                                                                      NumExp(1)))))),
                    AppExp(VarExp('fact'), NumExp(5)))
    print(exp)
    print(T_c(exp, VarExp('halt')))
