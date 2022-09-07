from cmd import Cmd
from moveengine import *
from chessengine import *

class  ChessInterface(Cmd):
    gamemode:bool = False

    __show_profile = False

    ponder_time = 10

    intro:str = (
    "Welcome to unnamed chess engine console\n"
    "Type \"help\" for help or \"help\" \"Command\" for help with a specific command"
    )
    
    prompt:str = "(chess)"

    me:MoveEngine = None

    ce:Engine = None

    cache:MoveEngine = None

    selected_moves:list[Move] = None

    def __new_turn(self):
        status = self.me.terminal_status

        if status == TerminalStatus.NotTerminal and self.me.in_check:
            print("Check!")

        if status == TerminalStatus.Checkmate:
            print("Checkmate!")
        if status == TerminalStatus.Stalemate:
            print("Stalemate")
        if status == TerminalStatus.Draw:
            print("Draw")

    def do_select(self,args):
        """
select \"Piece Position\"
--------------------------------------------------------
Select a piece to move 
lists valid moves for piece, use \"move\" to select move \n

example:  (Select piece on a2)
------------------------------------
(chess) select a2
0: Move object: Move p from a2 to a3
1: Move object: Move p from a2 to a4 
------------------------------------

        """
        try:
            x,y = BoardIO.convert_position(args)
            assert x >= 0 and x < 8 and y >= 0 and y < 8
        except:
            print("Invalid coordinates")
            return
            

        pos = Bitboard.get_pos(x,y)

        self.selected_moves = self.me.get_moves_pos(pos)

        for n,move in enumerate(self.selected_moves):
            print(f"{n}: {move}")

    def do_move(self,args):
        """
move \"Selected Move\"
--------------------------------------------------------
Choose a move out of selected moves to play
Piece must be selected using \"select\" before playing moving\n
Example: Move piece from a2 to a4
------------------------------------
(chess)select a2 
0: Move object: Move p from a2 to a3
1: Move object: Move p from a2 to a4 
(chess)move 1 
------------------------------------
        """

        try:
            move_num = int(args)
            move = self.selected_moves[move_num]
        except:
            print("Invalid move")
            return

        self.me.move(move)
        self.do_d(None)

        if self.gamemode:
            self.do_cpu(None)

        self.__new_turn()

    def do_d(self,args:str):
        """Displays current board"""
        logging.info(f"hash: {self.me.current_hash}")
        logging.info(f"FEN: {BoardIO.get_fen(self.me.board)}")
        print(f"Turn: {PieceColor.NUMBER_REPRESENTATION_FULL[self.me.board.turn]}")
        BoardIO.print_board(self.me.board)
        

    
    def do_fen(self,args:str):
        """
fen \"FEN\"
--------------------------------------------------------
Sets board FEN to specified FEN or displays FEN of current board \n
For information on FEN notation: https://www.chess.com/terms/fen-chess
------------------------------------\n
Example: set postiion to move 19 of Gary Kasparov vs Deep Blue rematch (match 6)
(https://www.chess.com/article/view/deep-blue-kasparov-chess)
------------------------------------
(chess) fen r1k4r/p2nb1p1/2b4p/1p1n1p2/2PP4/3Q1NB1/1P3PPP/R5K1 b - c3 0 19

Example: Get fen of current board
------------------------------------
(chess) fen
        """
        if args.strip() == "":
            print(BoardIO.get_fen(self.me.board))
            return
        try:
            self.me.set_fen(args)
        except:
            print("Invalid fen")
            return

        self.do_d(None)

    def do_list(self,args):
        """Lists all moves for the given position"""
        moves = self.me.get_moves()
    
        print(f"Moves: {len(moves)}")
        for move in moves:
            print(move)

    def do_undo(self,args):
        """Undoes previous move"""
        self.me.unmove()
        self.do_d(None)

    def do_profile(self,args:str):
        """Enables performance profiling of Chess Engine"""
        if args == "true":
            self.__show_profile = True
            print("Profiling enabled")
        elif args == "false":
            self.__show_profile = False
            print("Proifiling disabled")
        else:
            print("Invalid argument, enter true or false")

    def do_pondertime(self,args:str):
        """Sets the ponder time of the Chess Engine"""
        try:
            self.ponder_time = float(args)
            print(f"Ponder time set to {self.ponder_time:.2f} (s)")
        except ValueError:
            print("Please enter float")

    def do_perft(self,args):
        """
Evalutate perft up to a given depth 
https://www.chessprogramming.org/Perft
        """
        try:
            depth = int(args)
        except:
            print("Invalid integer")
            return

        me = self.me

        if depth == 1:
            print(f"Moves {me.perft(depth)}")
            return

        moves = me.get_moves()
        total = 0

        for move in moves:
           me.move(move)
           try:
                result = me.perft(depth-1)
           except:
                print(f"ERROR COMPUTING MOVE {move}")
           total += result
           print(f"{move.uci}: {result}")
           me.unmove()

        print(f"Nodes: {total}")

    def do_gamemode(self,args):
        """
Toggles game mode on or off. When game mode is on cpu will automattically make move after you move your piece.
        """
        self.gamemode = not self.gamemode

        if self.gamemode:
            print("Gamemode toggled on!")
        else:
            print("Gamemode toggled off!")

    def do_cpu(self,args):
        """
Finds the chess engine's top move and executes it
        """
        ce = self.ce

        ce.move_engine = deepcopy(self.me)

    
        if self.__show_profile:
            pr = cProfile.Profile()
            pr.enable()

        eval,move = ce.ponder(self.ponder_time)

        if self.__show_profile:
            pr.disable()
            s = io.StringIO()
            sortby = SortKey.CUMULATIVE
            ps = pstats.Stats(pr,stream=s).sort_stats(sortby)
            ps.print_stats()
            print(s.getvalue())


        print(f"Evaluation {eval}, move: {move}")
        self.me.move(move)
        self.do_d(None)
        self.__new_turn()
 
    def do_reset(self,args):
        """Resets board to starting position"""
        self.do_fen(FEN.START_POS)

    def do_debug(self,args):
        """Displays debugging info"""
        logging.basicConfig(level=logging.DEBUG)
        

    def do_cpugame(self,args):
        """Plays a game of computer vs computer"""
        while(1):
            if self.me.terminal_status != TerminalStatus.NotTerminal: break
            self.do_cpu(None)
            


    def __init__(self) -> None:
        super().__init__()
        self.cache = MoveCache()
        board = BoardIO.from_fen(FEN.START_POS)
        self.me = MoveEngine(board,self.cache)
        self.ce = Engine(self.cache,self.me)
        self.do_d(None)


def main():
    ChessInterface().cmdloop()




if __name__ == '__main__': main()