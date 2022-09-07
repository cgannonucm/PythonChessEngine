from copy import deepcopy
from moveengine import *
from evaluation import *
import time
import pstats
from pstats import SortKey
import time
from test import *
import chess
import chess.polyglot
import logging

class Node:
    """Rerpresents a node in alphabeta search"""
    best_node:"Node" = None

    move:Move = None
    
    best_move:Move = None
    
    score:int = None
    
    quiescence:bool = None
    
    beta_cut:bool = False

    transposition_read:bool = False

    def __init__(self,move:Move,best_move:Move,score:int,quiescence:bool,beta_cut:bool = False) -> None:
        self.move = move
        self.best_move = best_move
        self.score = score

        self.quiescence = quiescence
        self.beta_cut = beta_cut

    def __repr__(self) -> str:
        output = "Node object: "
        if self.move != None:
            output += f"Representing move: {self.move.uci}, "
        if self.best_move != None:
            output += f" best move found: {self.best_move.uci}, "
        else:
            output += "No move yet asigned, "
        output += f"score: {self.score} "
        if self.quiescence:
            output += ", quiescence node"
        output += f", beta cut: {self.beta_cut}"
        return output


class TranspositionTable:
    table_depth = 4
    __tables = None

    def add_entry(self,hash:int,depth_left:int,node:Node,alpha:int,beta:int):
        """Add entry to transposition table"""
        #Look at most recent table
        table = self.__tables[-1]
        

        #Add entry to our table if if the hash at the table has depth left of less than our current depth
        add = False
        if not hash in table:
            add = True
        elif table[hash][0] < depth_left:
            add = True
                
        if add:
            table[hash] = (depth_left,node)
    

    def attempt_read(self,hash:int,depth_left:int)->Node:
        """
        Reads entry from transposition table that corresponds to given hash if it exists and has a depth greater than or equal to depth left.
        If entry does not exist returns None. If entry exists returns (score,depth_left,c_nodes) for entry
        """
        #look through all our tables
        tables = self.__tables
        
        #Start at newest tables first
        for table in reversed(tables):
            #Look for hash in our table
            if hash in table:
                #Hash is in table, ensure a
                entry = table[hash]
                #Only read from table if it meets the depth specification
                if entry[0] >= depth_left:
                    return entry[1]
        #No entry found that meets depth specification return none
        return None

    
    def advance_turn(self):
        """Clears out old transpositions, prepares for new turn"""
        self.__tables.append({})
        self.__purge()

    def __purge(self):
        """Adds new transposition tables, trims transposition tables until they match the table depth"""
        while(1):
            if len(self.__tables) >= self.table_depth:
                del self.__tables[0]
            else:
                break




    def __init__(self,table_count:int = 2) -> None:
        self.__tables = [{}]
        self.table_depth = table_count



class Engine():

    MAXDEPTH = 50

    cache:MoveCache = None

    move_engine:MoveEngine = None

    presort = True

    select = None
    nodes = 0
    evaluations = []

    null_depth = 3
    table_depth = 4

    ALPHA_DEF:int = -100000000
    BETA_DEF:int = 100000000

    KEY_W_PROMO:int = 900
    KEY_W_ENPASSANT:int = 200
    KEY_W_KING_ATTACK:int = 50

    transpositions_read = 0

    PATH_OPENING = "opening/baron30.bin"
    """Path to opening book"""
    
    opening_book_mode:bool = True
    """If set to true will attempt to probe opening book"""

    __is_endgame:bool = False

    __depth_left:int = 0
    __c_depth:int = 0

    __last_ponder:Node = None

    __pondering:bool = False
    __t_start:float = None
    __t_ponder:float = None

    __p_wieghts_used = 0

    __folowing_left = False
    __left_node:Node = None
    __left_depth = 0
    __null_move_prunes = 0
    __node_count = 0

    debug = True

    transposition_table:TranspositionTable = None
    
    @property
    def board(self):
        return self.move_engine.board

    @property
    def turn(self):
        return self.board.turn

    class TimeUpException(Exception):
        pass

    def __check_stop(self):
        if self.__pondering:
            c_time = time.time()
            if c_time - self.__t_start > self.__t_ponder:
                raise Engine.TimeUpException("Time ran out on computation")

    def presort_key(self,move:Move):
        """The key for presorting moves for efficient alpha beta search"""
        #TODO incentivize bringing pieces out of danger
        if not self.presort: return 0

        turn = self.turn

        weight = 0

        if self.__pondering and self.__c_depth == self.__depth_left:
            self.__folowing_left = True



        if self.__pondering and self.__folowing_left:

            #Follow best move from last ponder to just above the horizon

            if self.__depth_left == 1:
                self.__folowing_left = False
            
            if self.__left_node == None or self.__left_node.best_move == None:
                self.__folowing_left = False

            if self.__folowing_left and self.__depth_left < self.__left_depth:
                move_id = move.id
                if move_id == self.__left_node.best_move.id:
                    weight = 10000 
                    self.__left_node = self.__left_node.best_node
                    self.__p_wieghts_used += 1
                    self.__left_depth = self.__depth_left
                    return weight

            if self.__c_depth == self.__depth_left and self.__last_ponder != None:
                move_id = move.id
                if move_id == self.__last_ponder.best_move.id:
                    weight = 10000
                    self.__folowing_left = True
                    self.__left_node = self.__last_ponder.best_node
                    self.__p_wieghts_used += 1
                    self.__left_depth = self.__c_depth

                    return weight

        #Reward promotion, if we can do it good change we should
        if move.move_type in MoveType.PROMOTIONS : weight += self.KEY_W_PROMO


        #Attempt to read score from transposition table
        #hash = ChessHashing.update(self.move_engine.current_hash,self.cache,move,self.board)
        #entry = self.transposition_table.attempt_read(hash,self.__depth_left - 1)
#
        #if entry != None:
        #    if entry[3].beta_cut:
        #        return 2000

        #reward enpassant
        if move.move_type == MoveType.ENPASSANT: weight += self.KEY_W_ENPASSANT


        piece_weight = Evaluation.PIECE_WIEGHTS_BASIC_KING[move.piece]
        if move.capture and move.piece != PieceType.KING:
            #Weight looking at any captures
           
            
            if not self.__is_bad_capture(move):
                if move.piece != PieceType.KING:
                    dif_weight = piece_weight - Evaluation.PIECE_WIEGHTS_BASIC[move.capure_piece]
                else:
                    dif_weight = Evaluation.PIECE_WIEGHTS_BASIC[move.capure_piece]
                weight += dif_weight if dif_weight > 0 else 50

        pos_tbl = PST.get_table(turn,move.piece,self.__is_endgame)

        #Look at moves that move us into a better position
        weight += pos_tbl[move.pos_to] - pos_tbl[move.pos_from]

       


        #Implement more wieghting here

        return weight

        
    def quiescence(self,alpha:int,beta:int,depth:int,p_move:Move)->Node:
        """
        Called at horizon nodes, evaluates captures until no captures are left
        Esentially just alpha beta search for captures
        https://www.chessprogramming.org/Quiescence_Search
        """
        #Check if we still have time
        self.__check_stop()

        score = Evaluation.evaluate(self.move_engine,alpha,beta,depth == 0,self.__is_endgame)
        if score >= beta:
            #Beta cutoff
            return Node(p_move,MoveProcessor.NULL_MOVE,score=beta,quiescence=True,beta_cut=True)

        #Delta Pruning
        #https://www.chessprogramming.org/Delta_Pruning#:~:text=Delta%20Pruning%2C,alpha%20for%20the%20current%20node.
        delta = 900
        if p_move.move_type == MoveType.PROMOTIONQUEEN:
            delta += 775

        if score < alpha - delta:
            return Node(p_move,MoveProcessor.NULL_MOVE,score=alpha,quiescence=True,beta_cut=False)


        #Capture search

        if score > alpha:
            alpha = score
        
        c_node = Node(p_move,best_move=MoveProcessor.NULL_MOVE, score=None, quiescence=True, beta_cut=False)

        def loop_captures(move:Move):
            nonlocal alpha,beta,c_node

            if self.__is_bad_capture(move): 
                #Bad capture keep searching
                return True
            
            #Alpha beta search for capture
            sub_node = self.quiescence(-beta,-alpha,depth + 1,move)
            score = -sub_node.score

            if score >= beta:
                #Beta cutoff
                c_node.best_move = move
                c_node.beta_cut = True
                c_node.best_node = sub_node
                alpha = beta
                return False
            
            if score > alpha:
                c_node.best_move = move
                c_node.best_node = sub_node
                alpha = score          

            return True
        
        def allow(move:Move)->bool:
            return move.capture
        #Loop through captures, TODO need move generator that only generates captures
        self.move_engine.loop_moves(loop_captures,None,allow)

        c_node.score = alpha

        return c_node

    def __is_bad_capture(self,move:Move):
        """Static capture evaluation, to determine if capture is good or not"""

        #Capturing with pawn always good
        if move.piece == PieceType.PAWN:
            return False
        #Capturing to increase value good
        if Evaluation.PIECE_WIEGHTS_BASIC_KING[move.piece] <= Evaluation.PIECE_WIEGHTS_BASIC_KING[move.capure_piece] + 200:
            return False

        #Piece weight is less than captured piece, if captured piece is defended by pawn abort
        if self.__is_defended_by_pawn(move.caputre_pos,PieceColor.reverse_color(self.board.turn)):
            return True

        return False 

    def __is_defended_by_pawn(self,pos,color):
        """Returns true if the position is defended by a pawn of given color"""
        pawn_board = self.board.get_board_piece(color,PieceType.PAWN)
        #Check if a pawn is defending by seing if a pawn placed at that square of oposite color could capture another pawn
        mask = self.cache.bitm_moves_p_a_b[pos] if color == PieceColor.WHITE else self.cache.bitm_moves_p_a_w[pos]
        return (pawn_board.value & mask.value) == 0
        
    def __null_evaluation(self,depth_left:int,alpha:int,beta:int,p_move:Move)->bool:        
        """Attempt evaluation of null move returns True if null move triggered a beta cutoff false if otherwise"""
        
        me = self.move_engine
        #No null moves on first loop
        if depth_left == self.__c_depth:
            return False
        #No null moves in endgame, for now
        if self.__is_endgame:
            return False
        #No null moves when king is in check 
        if me.in_check:
            return False

        if depth_left > self.null_depth:
            return False

        #No need to prove null moves below a certain depth
        depth_new = depth_left - 1 - self.null_depth
        if depth_new < 0:
            depth_new = 0
        
        #We are good to go for null move
        me.move(MoveProcessor.NULL_MOVE)
        

        #Note we do not allow null move is this alphabeta search
        sub_node = self.alphabeta(depth_new, -beta, -alpha,MoveProcessor.NULL_MOVE,False)
        score = -sub_node.score

        #Undo move        
        me.unmove()

        #Finally check against beta to see if we triggered a beta cutoff
        return score >= beta
    
    def alphabeta(self,depth_left:int,alpha:int,beta:int,p_move:Move,allow_null:bool = True)->Node:
        """Alpha beta search algorithm - https://www.chessprogramming.org/Alpha-Beta """
        #Check if we still have time
        self.__check_stop()

        self.__depth_left = depth_left

        c_node = Node(p_move,best_move=MoveProcessor.NULL_MOVE,score=None,quiescence=False,beta_cut=False) 

        #Attempt transposition read
        entry_node = self.transposition_table.attempt_read(self.move_engine.current_hash,depth_left)
        if entry_node != None and not self.__folowing_left:
            
            #Case not beta cut, entry score gives lower bound. if lower bound is less than alpha we can return alpha
            #as there is no chance of improving alpha
            if not entry_node.beta_cut:
                if entry_node.score <= alpha:
                    pass
                    self.transpositions_read += 1
                    c_node.score = alpha
                    return c_node
            #Case: beta cut: entry score gives upper bound. We can skip this node if upper bound is greater than beta
            #Because we are guaranteed a beta cut
            else:
                if entry_node.score >= beta:
                    self.transpositions_read += 1

                    c_node.score = beta
                    c_node.best_move = entry_node.best_move
                    c_node.best_node = entry_node.best_node
                    c_node.beta_cut = True

                    return c_node

        self.__node_count += 1

        #We are at horizon, return evaluation
        if depth_left == 0:
            self.nodes += 1
            return self.quiescence(alpha,beta,0,p_move)

        
        is_terminal = True


        #Attempt null move evaluation if we are allowing null evaluation and we are not following the best node from last search
        if allow_null and not self.__folowing_left:
            null_eval = self.__null_evaluation(depth_left,alpha,beta,p_move)
            if null_eval:
                self.__null_move_prunes += 1
                c_node.score = beta
                c_node.beta_cut = True
                return c_node



        #Evaluate moves
        def move_evaluate(move:Move)->bool:
            nonlocal alpha,beta,c_node,self,depth_left,p_move,is_terminal

            #Alpha beta for lower next turn's alpha beta search
            new_alpha = -beta
            new_beta = -alpha

            #This node is not terminal as we were able to evaluate 1 node
            is_terminal = False

            #Run alpha beta for this move and get score
            sub_node = self.alphabeta(depth_left - 1,new_alpha, new_beta,move,allow_null)
            score = -sub_node.score

            if score >= beta:
                #Beta cutoff
                c_node.best_move = move
                c_node.beta_cut = True
                c_node.best_node = sub_node
                alpha = beta
                return False
            
            #Check if move approves upon score
            if score > alpha:
                c_node.best_move = move
                c_node.best_node = None
                alpha = score

            

            return True        

        #Sort moves if we are halfway to horizon or less this is arbitrary right now 
        #Tune this later. We gain a lot from sorting at the beginning of search very little after that
        #if (self.__c_depth - depth_left)/self.__c_depth <= 0.75:
        self.move_engine.loop_moves(move_evaluate,self.presort_key,None)
        #else:
            #self.move_engine.loop_moves(move_evaluate,None,None)
        score = alpha

        if is_terminal:
            terminal_status = self.move_engine.terminal_status
            if terminal_status == TerminalStatus.Draw or terminal_status == TerminalStatus.Stalemate:
                score = 0
            elif terminal_status == TerminalStatus.Checkmate:
                #We are in check this must be checkmate, add an incentive for faster checkmates by addubg depth left to score
                #Coeficient for checkmate if it's whites turn should be -1000 as white got checkmated if it's blacks turn it should be -1000 as black got checkmated
                #At horizon we reuturn evaluate() whose sign is positive if player whose turn it is is winning, no negation since we do not negate evaluate()
                score = -(Evaluation.WEIGHT_CHECKMATE + 1000*depth_left)
            else:
                raise Exception("Node is terminal but no terminal status is asigned")

            c_node.best_move = MoveProcessor.NULL_MOVE
            c_node.best_node = None

        c_node.score = score


        #Record node in transposition table
        self.transposition_table.add_entry(self.move_engine.current_hash,depth_left,c_node,alpha,beta)

        
        
        return c_node

    def search_tree(self,depth:int)->Node:
        """Searches tree for best moves using alpha beta search algorithm https://www.chessprogramming.org/Alpha-Beta"""
        assert depth != 0
        #Check to see if we have time
        self.__check_stop()


        #Enable null moves
        allow_null = self.move_engine.allow_null
        self.move_engine.allow_null = True

        #Store wether we are in endgame or not
        self.__is_endgame = Evaluation.is_endgame(self.move_engine)
        
        self.__c_depth = depth
        self.__depth_left = depth
        result_node = self.alphabeta(depth,Engine.ALPHA_DEF,Engine.BETA_DEF,MoveProcessor.NULL_MOVE,True)

        self.move_engine.allow_null = allow_null

        return result_node




    def __attempt_opening_book_read(self)->Move:
        """Attempts to read move from opening book \n
        uses python chess to interface with polyglot book \n
        book used - https://www.chessprogramming.net/new-version-of-the-baron-v3-43-plus-the-barons-polyglot-opening-book/ \n
        returns None if no move can be found \n
        """
        #If we are not in opening book move do not attempt read
        if not self.opening_book_mode: return None
        #Convert from our board format to python board format with 
        py_board = chess.Board(BoardIO.get_fen(self.board))
        with chess.polyglot.open_reader(self.PATH_OPENING) as reader:
            try:
                entry = reader.weighted_choice(py_board)
            except IndexError:
                #No move can be read from opening book
                return None
        #Return the move
        return PseudoMoveGenerator.from_uci(self.board,self.cache,entry.move.uci())
    
    


        

    def ponder(self,time_ponder:int)->tuple[int,Move]:
        """
        Search for best move for a set ammount of time\n
        time_ponder - the time to ponder the given move
        """
        #Update transposition tables
        self.transposition_table.advance_turn()

        #Attempt opening book read
        opening_move = self.__attempt_opening_book_read()
        if opening_move != None:
            logging.info("Opening book move read")
            return (0,opening_move)

        #Continue to ponder even if an opening move is read to increase transposition table
        self.__p_wieghts_used = 0

        #Search tree to find move for depth of 1 so even if we timeout we still have move to
        self.__last_ponder = self.search_tree(1)

        #Todo replace deepcopy by tracking the total depth and undoing moves 
        me_copy1 = deepcopy(self.move_engine)

        self.move_engine = me_copy1

        me_copy2 = deepcopy(self.move_engine)


        #Set up pondering variables
        self.__pondering = True
        self.__t_start = time.time()
        self.__t_ponder = time_ponder
        time_up = False

        prunes = self.__null_move_prunes
        reads = self.transpositions_read
        node_count =  self.__node_count

        for i in range(2,self.MAXDEPTH + 1):
            try:
                #Keep track of variables
                prunes = self.__null_move_prunes
                reads = self.transpositions_read
                node_count =  self.__node_count

                self.__reset_counters()
                self.__last_ponder = self.search_tree(i)
            except Engine.TimeUpException:
                logging.info(f"Depth reached in {time_ponder:.2f} (s) ponder: {i - 1}")
                time_up = True
                break
            except Exception as e:
                logging.info(f"Exception occoured searching moves depth f{i}")
                logging.info(self.move_engine.move_stack)
                raise e
        
        if not time_up:
            print(f"Maximum Depth ({self.MAXDEPTH}) reached in {time_ponder:.2f}")
            pass
    
        self.__pondering = False
        self.__t_start = None
        self.__t_ponder = None
        self.__depth_left = 0
        self.__c_depth = 0

        

        self.move_engine = me_copy2

        best_move = self.__last_ponder.best_move
        score = self.__last_ponder.score

        # (branch_factor) ^ max_depth = total_node_count
        # => branch_factor = (total_node_count) ^ 1 / max_depth
        branch_factor = node_count ** (1/i) 

        logging.info(f"Transposition entries read {reads}")
        logging.info(f"Null move prunes: {prunes}")
        logging.info(f"Branching factor: {branch_factor:.2f}")

        self.__reset_counters()
        
        self.__last_ponder = None

        if opening_move != None:
            return (0,opening_move)
        
        return (score,best_move)
    
    def __reset_counters(self):
        self.__null_move_prunes = 0
        self.__p_wieghts_used = 0
        self.transpositions_read = 0
        self.__node_count = 0
        
    def __init__(self,cache:MoveCache,move_engine:MoveEngine == None) -> None:
        if self.debug:
            logging.basicConfig(level=logging.DEBUG)

        self.cache = cache
        _me = move_engine
        self.transposition_table = TranspositionTable()
        if _me == None:
            board = BoardIO.from_fen(FEN.START_POS)
            _me = MoveEngine(board,cache)
        self.move_engine = deepcopy(_me)
            
 
def test():
    show_perf = True
    if show_perf:
        pr = cProfile.Profile()
        pr.enable()

    #board = BoardIO.from_fen("q7/5k2/8/1p6/5QP1/P4N2/5PK1/8 b - - 10 60")
    #board = BoardIO.from_fen(FEN.START_POS)
    board  = BoardIO.from_fen("8/4k3/4P3/4K3/8/8/8/8 b - - 14 13")
    cache = MoveCache()
    ce = Engine(cache,MoveEngine(board,cache))
    ce.ponder(2)
    ce.ponder(100)
    if show_perf:
        pr.disable()
        s = io.StringIO()
        sortby = SortKey.CUMULATIVE
        ps = pstats.Stats(pr,stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())

def test2():
    board = BoardIO.from_fen("8/p4p1b/P1p2k2/2N2p2/5Kp1/8/7P/8 b - - 8 50")
    cache = MoveCache()
    ce = Engine(cache,board)
    ce.search_tree(2)

if __name__ == '__main__':
    test()