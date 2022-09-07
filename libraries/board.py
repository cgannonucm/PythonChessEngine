from dataclasses import dataclass
import numpy as np
import time
import pstats
from pstats import SortKey
import time
import cProfile
import io 
from ctypes import c_uint64
from copy import copy
from math import log2,floor
from abc import ABC, abstractmethod


class FEN:
    """
    Position 3,4,5 are from
    From chessprogramming.org/Perft_Results
    """

    START_POS = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    
    """Legal move generator basic tests"""
    PIN_TEST_ROOK1 = "8/k7/4r3/8/4P3/8/8/4K3 w - - 0 1"
    PIN_TEST_ROOK2 = "8/k7/4r3/8/4N3/8/8/4K3 w - - 0 1"
    PIN_TEST_ROOK3 = "8/k7/4r3/8/4R3/8/8/4K3 w - - 0 1"

    PIN_TEST_QUEEN1 = "8/k7/4q3/8/4N3/8/8/4K3 w - - 0 1"
    PIN_TEST_QUEEN2 = "8/k7/4qq2/8/4Q3/8/8/4K3 w - - 0 1"
    CHECK_TEST_1 = "K7/4Q3/8/4B3/8/4k3/8/8 w - - 0 1"
    CHECK_TEST_2 = "K7/4Q3/8/4B3/4r3/4k3/8/8 w - - 0 1"

    PIN_TEST_MULTI = "k7/4r3/1q2q2b/8/3PPP2/4K3/8/8 w - - 0 1"
    PIN_TEST_MULTI_BLOCKER = "k7/4r3/1q2q2b/2PPPPP1/3PPP2/4K3/8/8 w - - 0 1"
    KING_MOVE_TEST = "8/k7/3rrr2/8/4R3/8/8/4K3 w - - 0 1"

    """Debug"""
    DEBUG_1 = "rnbqkbnr/p1pppppp/8/8/1p6/3P4/PPPKPPPP/RNBQ1BNR w kq - 0 1"
    DEBUG_2 = "rnbqkbnr/p1pppppp/8/8/1p6/2PP4/PP1KPPPP/RNBQ1BNR w kq - 0 1"
    DEBUG_3 = "rnb1kbnr/pppp1ppp/5q2/4p3/5P2/8/PPPPPKPP/RNBQ1BNR w kq - 0 1"
    

    """Tests for square attacks"""
    ATTACK_TEST_1 = "3RK3/8/8/8/8/8/8/5k2 w - - 0 1"

    
    #Debug positions
    #https://www.chessprogramming.org/Perft_Results
    POS_2 = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq -"
    POS_3 = "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - -"
    POS_4 = "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1"
    POS_5 = "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8"
    POS_6 = "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10 "
    

    #Engine testing positions
    #Tests looking ahead 2 moves, finding material advantage, these two positions are same but with color flipped
    TEST_POS_BASIC_MAT_1 = "1K6/8/3r2Q1/8/8/b7/8/4k3 w - - 0 1"
    TEST_POS_BASIC_MAT_2 = "1k6/8/3R2q1/8/8/B7/8/4K3 b - - 0 1"

    #One move checkmating ability
    #Checkmate in 1
    TEST_POS_BASIC_MATE_1 = "1R5K/2R5/8/8/8/8/8/k7 w - - 0 1"
    TEST_POS_BASIC_MATE_2 = "1r5k/2r5/8/8/8/8/8/K7 b - - 0 1"


class PieceType:
    PAWN = 0
    KNIGHT = 1
    BISHOP = 2
    ROOK = 3
    QUEEN = 4
    KING = 5

    SLIDING_PIECES = [ROOK,QUEEN,BISHOP]

    STRING_ABREVIATIONS = {"p":PAWN,"n":KNIGHT,"b":BISHOP,"r":ROOK,"k":KING,"q":QUEEN}
    NUMBER_REPRESENTATIONS = {PAWN:"p", KNIGHT:"n", BISHOP:"b", ROOK:"r", KING:"k", QUEEN:"q"}

class BitTwiddle:
    """Class for well twiddling with bits"""
    one = c_uint64(1).value
    zero = c_uint64(0).value
    debruijconst = c_uint64(0x03f79d71b4cb0a89)
    
    """
    I have implemented this algorithm because int.bitcount is not compatible with pypy, I have no fucking clue what it does and if it breaks
    it will cause a lot of trouble. I don't like this.
    """
    lookup_table = [
        0,  1, 48,  2, 57, 49, 28,  3,
        61, 58, 50, 42, 38, 29, 17,  4,
        62, 55, 59, 36, 53, 51, 43, 22,
        45, 39, 33, 30, 24, 18, 12,  5,
        63, 47, 56, 27, 60, 41, 37, 16,
        54, 35, 52, 21, 44, 32, 23, 11,
        46, 26, 40, 15, 34, 20, 31, 10,
        25, 14, 19,  9, 13,  8,  7,  6
    ]
    

    def bitscan_forward(bb:"Bitboard")->int:
        """
        https://www.chessprogramming.org/BitScan
        bitScanForward
        @author Martin Läuter (1997)
        Charles E. Leiserson
        Harald Prokop
        Keith H. Randall
        """
        assert bb.value != 0
        index = c_uint64(((bb.value & -bb.value) * BitTwiddle.debruijconst.value)).value >> 58
        return BitTwiddle.lookup_table[index]
class HashUtil(ABC):
    """Hashing utility abstrcact class"""
    @abstractmethod
    def get_hash_piece(self,piece:int,square:int,color:int)->int:
        pass
    
    @abstractmethod
    def get_hash_castling_rights(self,castle_rights:"CastleRights")->int:
        pass

    @abstractmethod
    def get_hash_turn(self,turn:int)->int:
        pass
    
    @abstractmethod
    def get_hash_enpassant(self,target:int)->int:
        pass

@dataclass
class MoveInstruction:
    """Provides all the details for what happened during the move"""
    move_from:int
    move_from_piece:int
    move_from_color:int

    move_to:int
    move_to_piece:int

    capture:bool
    capture_pos:int
    capture_piece:int
    capture_color:int
    half_move_clock:int
    old_half_clock:int

    castling_rights_previous:tuple[tuple[bool,bool]]
    castling_rights_current:tuple[tuple[bool,bool]]

    enpassant_target_previous:int
    enpassant_target_current:int

    castle:bool
    rook_pos_from:bool
    rook_pos_to:bool
    null:bool = False

class Bitboard:
    """A bitboard based on c_uint64"""
    value = BitTwiddle.zero

    def set(self,index):
        self.value |= (1 << index)

    def unset(self,index):
        self.value &= ~(1 << index)
        
    def get(self,index:int):
        mask = (self.value >> index)
        return mask & BitTwiddle.one

    def occupied(self,index:int):
        _get = self.get(index)
        return _get == 1

    def __repr__(self) -> str:
        return f"{self.value:064b}"

    @staticmethod
    def merge(bitboard1:"Bitboard",bitboard2:"Bitboard"):
        return bitboard1.value | bitboard2.value

    @staticmethod
    def get_x(pos:int)->int:
        """Gets x position on chess board for a position in the bitboard"""
        return pos % 8

    @staticmethod
    def get_y(pos:int)->int:
        """Gets y position on chess board for a position in the bitboard"""
        return pos // 8

    @staticmethod
    def get_pos_2d(pos:int)->tuple[int,int]:
        return (Bitboard.get_x(pos),Bitboard.get_y(pos))

    @staticmethod
    def shift_check(pos,direction:tuple[int,int])->int:
        """Tries to shift a position in given direction, returns none if position goes off of board"""
        #Attempt horizontal shift
        y0 = Bitboard.get_y(pos)
        shifted_horizontal = pos + direction[0]
        y1 = Bitboard.get_y(shifted_horizontal)
        #Check if we are on same y-level if not we shifted off of board
        if y0 != y1: return None

        #Attempt vertical shift
        shifted = shifted_horizontal + 8 * direction[1]
        #See if we are outside bounds, if we are we have shifted off of board
        if shifted < 0 or shifted > 63: return None
        #Shift sucessfull return shift
        return shifted

    @staticmethod
    def get_pos(x:int,y:int):
        return x + 8 * y

    @staticmethod
    def bitscan_reverse(bb:"Bitboard"):
        assert bb != 0
        return floor(log2(bb.value))

    @staticmethod
    def bitscan_forward(bb:"Bitboard"):
        """Bitscan forward algorithm https://www.chessprogramming.org/BitScan"""
        return BitTwiddle.bitscan_forward(bb)

    @staticmethod
    def bitscan(bb:"Bitboard",forward:bool):
        if forward: return Bitboard.bitscan_forward(bb)
        return Bitboard.bitscan_reverse(bb)

    @staticmethod
    def popcount(bb:"Bitboard"):
        count = 0
        while(1):
            if bb.value == 0: break
            c_x = Bitboard.bitscan_reverse(bb)
            bb.unset(c_x)
            count += 1
            
        return count
        

    def __init__(self,val=None) -> None:
        if val == None: return
        self.value = val
        

class PieceColor:
    WHITE = 0
    BLACK = 1

    STRING_ABREVIATIONS = {"w":WHITE,"b":BLACK}
    NUMBER_REPRESENTATION = {WHITE:"w",BLACK:"b"}
    NUMBER_REPRESENTATION_FULL = {WHITE:"White", BLACK:"Black"}


    @staticmethod
    def reverse_color(color:int)->int:
        """Swaps colors from black to white and white to black"""
        return PieceColor.BLACK if color == PieceColor.WHITE else PieceColor.WHITE

class CastleRights(Bitboard):
    

    def __get_castle_pos(self,color,dir):
        return 2 * color + dir

    def enable_castle(self,color,dir):
        """
        Enables castling for pices of color specified by color and direction specified by direction
        direction - 0 for castle west 1 for castle east
        """
        self.set(self.__get_castle_pos(color,dir))

    def disable_castle(self,color,dir):
        """
        Disables castling for pices of color specified by color and direction specified by direction
        direction - 0 for castle west 1 for castle east
        """
        self.unset(self.__get_castle_pos(color,dir))

    def get_castling_rights(self,color,dir):
        """
        Checks for castling rights in a given direction and color
        direction - 0 for castle west 1 for castle east
        """
        return self.occupied(self.__get_castle_pos(color,dir))

    def has_castle_rights(self,color):
        """Wether a side has castling rights for either side"""
        return self.occupied(self.__get_castle_pos(color,0)) or self.occupied(self.__get_castle_pos(color,1))

    def __repr__(self) -> str:
        return f"{self.value:04b}"

    def __init__(self,value = None) -> None:
        if value == None: 
            self.value = 0b0000
            return
        self.value = value
        

    def copy(self)->"CastleRights":
        return CastleRights(self.value)


class Board:
    BOARDSQUARELENGTH = 8

    #Keeps track of squares ocupied and squares occupied by a given color
    squares:Bitboard = None
    squares_color:list[Bitboard] = None

    #Keeps track of piece locations for each of pieces and colors
    pieces:list[Bitboard] = None

    #Keeps track of locations that have pieces
    locations:list[list[int]] = None

    #Keep track of enpassant target
    enpassant_target = None
    castle_rights:CastleRights = None

    #Keep track of turn color
    turn:int = None

    #Moves and half move clock
    full_move:int = 1
    """Number of full moves in game"""
    half_move:int = 0
    """Number of half moves since last pawn push or piece capture"""

    def get_list_pos(self,color:int,piece_type:int):
        add = 0 if color == PieceColor.WHITE else 6
        return add + piece_type

    def add(self,pos,color,piece_type)->None:
        """Adds a piece of given color and piece type at a specified color"""
        assert pos >= 0 and pos < 64
        list_pos = self.get_list_pos(color,piece_type)

        self.pieces[list_pos].set(pos)
        self.locations[list_pos].append(pos)

        self.squares.set(pos)
        self.squares_color[color].set(pos)

    def delete(self,pos,color,piece_type)->None:
        list_pos = self.get_list_pos(color,piece_type)

        self.pieces[list_pos].unset(pos)
        self.locations[list_pos].remove(pos)

        self.squares.unset(pos)
        self.squares_color[color].unset(pos)
        

    def get_color(self,pos)->int:
        """Returns color of piece at a given position, None if piece does not exist"""
        if self.squares_color[PieceColor.WHITE].occupied(pos): return PieceColor.WHITE
        if self.squares_color[PieceColor.BLACK].occupied(pos): return PieceColor.BLACK
        return None

    def get_piece_type(self,pos,color)->int:
        """Returns the piece type of a piece at given position and color, None if piece does not exist"""
        
        for piece_type in range(6):
            list_pos = self.get_list_pos(color,piece_type)
            
            if self.pieces[list_pos].occupied(pos):
                return piece_type
        
        return None

    def get_locations_piece(self,color:int,piece_type:int)->list[int]:
        """Gets locations of all pieces of gieven piece type and color"""
        return self.locations[self.get_list_pos(color,piece_type)]

    def get_board_piece(self,color:int,piece_type:int)->Bitboard:
        """Gets a bitboard with pieces of given piece type and color toggled on"""
        return self.pieces[self.get_list_pos(color,piece_type)]

    def get(self,pos)->tuple[int,int]:
        """Returns piece color and piece type if piece exists otherwise returns none if no piece exists at that position"""
        color = self.get_color(pos)
        if color == None: return (None,None)
        piece_type = self.get_piece_type(pos,color)
        return (color, piece_type)
    
    def occupied(self,pos:int)->bool:
        """Returns true if square is occupied false if not"""
        return self.squares.occupied(pos)

    def get_piece_count(self,color,piece_type):
        """Returns the number of pieces on board of the given color and piece_type"""
        return len(self.get_locations_piece(color,piece_type))

    def copy(self)->"Board":
        """Very slow should not be used during move making and unmaking"""
        new_board = Board(init=False)

        #Keeps track of squares ocupied and squares occupied by a given color
        new_board.squares = copy(self.squares)
        new_board.squares_color:list[Bitboard] = [copy(bb) for bb in self.squares_color]

        #Keeps track of piece locations for each of pieces and colors
        new_board.pieces = [copy(bb) for bb in self.pieces]

        #Keeps track of locations that have pieces
        new_board.locations = [copy(locs) for locs in self.locations]

        #Keep track of enpassant target
        new_board.enpassant_target = self.enpassant_target
        new_board.castle_rights = copy(self.castle_rights)

        #Keep track of turn color
        new_board.turn = self.turn

        return new_board


    def move(self,instruction:MoveInstruction):
        """Executes a move using a move instruction"""
        #If move is not the null move check for moves / captures / special moves
        if not instruction.null:
        #Remove capture if the move was a capture
            if instruction.capture:
                self.delete(instruction.capture_pos,instruction.capture_color,instruction.capture_piece)
            elif instruction.castle:
                #Remove rook from old position and add to new position
                self.delete(instruction.rook_pos_from,instruction.move_from_color,piece_type=PieceType.ROOK)
                self.add(instruction.rook_pos_to,instruction.move_from_color,piece_type=PieceType.ROOK)

            #Remove piece from location we are moving from
            self.delete(instruction.move_from,instruction.move_from_color,instruction.move_from_piece)

            #Add in piece at location we are moving to
            self.add(instruction.move_to,instruction.move_from_color,instruction.move_to_piece)

        #Update castling rights
        self.castle_rights = instruction.castling_rights_current

        #Update enpassant target
        self.enpassant_target = instruction.enpassant_target_current

        #Advance turn, advance move clock
        if self.turn == PieceColor.BLACK:
            self.full_move += 1
        self.turn = PieceColor.reverse_color(self.turn)

        #Set half move clock
        self.half_move = instruction.half_move_clock

    def undo(self,instruction:MoveInstruction):
        """Undoes a move that is described by move instruction"""
        if not instruction.null:
            #Remove piece from it's current location
            self.delete(instruction.move_to,instruction.move_from_color,instruction.move_to_piece)

            #And put it back at it's previous location
            self.add(instruction.move_from,instruction.move_from_color,instruction.move_from_piece)

            #If there was a capture put piece back
            if instruction.capture:
                self.add(instruction.capture_pos,instruction.capture_color,instruction.capture_piece)
            elif instruction.castle:
                #Remove rook and place it back where it started
                self.delete(instruction.rook_pos_to,color=instruction.move_from_color,piece_type=PieceType.ROOK)
                self.add(instruction.rook_pos_from,color=instruction.move_from_color,piece_type=PieceType.ROOK)

        #Restore castling rights and enppassant target
        self.castle_rights = instruction.castling_rights_previous

        #Restor enpassant target
        self.enpassant_target = instruction.enpassant_target_previous

        #Adjust move clock, revert turn
        if self.turn == PieceColor.WHITE:
            self.full_move -= 1
        self.turn = PieceColor.reverse_color(self.turn)

        #Reset half move clock
        self.half_move = instruction.old_half_clock

    @property
    def enpassant_square(self)->int:
        """
        Board stores the location of the pawn that is available for enpassant capture
        Converts from this target location to the capture location IE the location a pawn
        would be at if it captured enpassant target in enpassant move
        """
        #No need to check if enpassant target is on board. Because if it is legal capture it must be 4th or 5th rank
        #Color white - enpassant pawn - black shift up board -> - shift
        shift = -8 if self.turn == PieceColor.WHITE else 8
        return self.enpassant_target + shift

    def get_piece_locations_color(self,color:int):
        if color == PieceColor.WHITE: return self.locations[0:6]
        return self.locations[6:12]        
    


    def __init__(self,init:bool = True) -> None:
        """Creates a board, if init is true initializes board. Otherwise all other properites are none"""
        if not init: return

        self.pieces = []
        self.locations = []
        
        for index in range(12):
            self.pieces.append(Bitboard(0))
            self.locations.append([])

        
        self.squares = Bitboard()
        self.squares_color = [Bitboard(0), Bitboard(0)]

        self.castle_rights = CastleRights()

        self.turn = 0


class BoardIO:
    """Handles inputing and outping of Chess Boards"""

    FILES_INT = {"a":0, "b":1, "c":2, "d":3,"e":4,"f":5,"g":6,"h":7}
    FILES_STR = {0:"a", 1:"b", 2:"c", 3:"d",4:"e",5:"f",6:"g",7:"h"}

    @staticmethod
    def __parse_positions(fen:str,board:Board)->None:
        """Parses piece positions from fen string"""
        SEPERATOR_ROW = "/" 
        SEPERATOR_SECTION = " "

        lenth = 8

        position_str = fen.split(SEPERATOR_SECTION)[0]

        rows = position_str.split(SEPERATOR_ROW)

        #Ensure we are within chess board
        if len(rows) != lenth: raise Exception("POSITION OUTSIDE OF 8X8 CHESSBOARD REFRENCED IN FEN STRING PROBLEM IN Y POSITION")
        
        #Keep track of both kings
        king_w_count = 0
        king_b_count = 0
        
        c_x = int(-1)
        for y,row in enumerate(rows):
            

            for ch in row:
                last_position = None

                try:
                    #Ensure we don't get 2 numbers in a row 
                    if last_position == False: raise ValueError("2 POSITIONAL ARGUMENTS IN A ROW, THIS IS NOT ALLOWED")

                    c_x += int(ch)
                    last_position = False

                    continue
                except ValueError:
                    c_x += 1
                    
                    #Ensure piece type is valid
                    if not ch.lower() in PieceType.STRING_ABREVIATIONS : raise ValueError(f"INVALID PIECE \"{ch}\" VALID PIECES ARE {PieceType.STRING_ABREVIATIONS.keys()}")
                    #Ensure we are within chess board

                    is_capital = ch.lower() == ch

                    piece_type = PieceType.STRING_ABREVIATIONS[ch.lower()]

                    piece_color = 1 if is_capital else 0

                    #Keep track of king
                    if piece_type == PieceType.KING:
                        king_w_count += 1 if piece_color == 0 else 0
                        king_b_count += 1 if piece_color == 1 else 0

                    last_position = True

                    board.add(c_x,piece_color,piece_type)

        
        if king_w_count != 1: raise ValueError("INVALID NUMBER OF WHITE KINGS, WHITE MUST 1 KING EXACTLY")
        if king_b_count != 1: raise ValueError("INVALID NUMBER OF BLACK KINGS, BLACK MUST 1 KING EXACTLY")

    def convert_position(pos_str:str) -> tuple[int,int]:
        file = pos_str[0]
        rank = pos_str[1]

        return (BoardIO.FILES_INT[file], 8-int(rank))

    def convert_position_bit(pos_str:str) -> int:
        return Bitboard.get_pos(*BoardIO.convert_position(pos_str))

    @staticmethod
    def from_fen(fen:str,board:Board = None) -> Board:
        "Sets board according to fen string https://www.chess.com/terms/fen-chess "
        board = Board() if board == None else board
        BoardIO.__parse_positions(fen,board)
        #Parse board properties
        split_str = fen.split(" ")
        #Turn info is stored at position 1, casttling rights denoted at position 2 and enpassant target noted at position 3
        #Parse turn info
        turn_str = split_str[1]
        if turn_str == "w": board.turn = PieceColor.WHITE
        elif turn_str == "b": board.turn = PieceColor.BLACK
        else: raise ValueError("INVALID TURN COLOR")
        #Set castling rights if castle rights is "-" -> no side has right to castle
        castle_str = split_str[2]
        if castle_str != "-":    
            for char in castle_str:
                #Upper case letter -> castle rights white lower case -> castle rights black
                #"K" -> kingside castle rights, "Q"-> queenside castling rights
                color = PieceColor.WHITE if char.capitalize() == char else PieceColor.BLACK
                if char.lower() == "k": side = 1
                elif char.lower() == "q": side = 0
                else: raise ValueError("Invalid Castling rights")
                board.castle_rights.enable_castle(color,side)

        #Set enpassant targets, "-" -> no en passant target
        pas_str = split_str[3]
        #TODO Implement
        if pas_str == "-":
            board.enpassant_target = None
        else:
            board.enpassant_target = Bitboard.get_pos(*BoardIO.convert_position(pas_str))
        
        if len(split_str) == 6:
            #Try to parse half move / full move. Not always included
            try:
                board.half_move = int(split_str[4])
                board.full_move = int(split_str[5])
            except ValueError:
                pass
        
        return board

    @staticmethod
    def __output_positions(board:Board):
        #Convert positons to dictionary
        pos_dict:dict[int,tuple[int,int]] = {}

        for color in range(2):
            for piece_type in range(6):
                for pos in board.get_locations_piece(color,piece_type):
                    pos_dict[pos] = (color,piece_type)

        out = ""
        
        empty_squares = 0

        for pos in range(64):

            if pos in pos_dict:

                color,piece_type = board.get(pos)

                piece_str = PieceType.NUMBER_REPRESENTATIONS[piece_type]

                piece_str = piece_str.capitalize() if color == PieceColor.WHITE else piece_str

                if empty_squares != 0:
                    out += str(empty_squares)
                out += piece_str
                
                empty_squares = 0
                
            else:
                empty_squares += 1
            
            if (pos + 1) % 8 == 0:
                    if empty_squares != 0: 
                        out += str(empty_squares)
                    if pos != 63:
                        out += "/"
                    empty_squares = 0


        return out
    


    @staticmethod
    def get_fen(board:Board):
        """Gets FEN of board state \n
         https://www.chess.com/terms/fen-chess
        """

        output = BoardIO.__output_positions(board)

        #Turn
        output += f" {PieceColor.NUMBER_REPRESENTATION[board.turn]} "

        #Castling rights
        if board.castle_rights.get_castling_rights(PieceColor.WHITE,1):
            output += "K"
        if board.castle_rights.get_castling_rights(PieceColor.WHITE,0):
            output += "Q"
        if board.castle_rights.get_castling_rights(PieceColor.BLACK,1):
            output += "k"
        if board.castle_rights.get_castling_rights(PieceColor.BLACK,0):
            output += "q"
        if not board.castle_rights.has_castle_rights(PieceColor.WHITE) and not board.castle_rights.has_castle_rights(PieceColor.BLACK):
            output += "-"

        #Enpassant target
        if board.enpassant_target != None:
            #Board enpassant target gives the postiion of the pawn that is capturable via enpassant
            #FEN represents this as the capture square
            output += " " + BoardIO.to_standard_coords(board.enpassant_square)
        else:
            output += " -"

        #Half move / full moves
        output += f" {board.half_move}"
        output += f" {board.full_move}"

        return output

    @staticmethod
    def print_board(board:Board):
        print(f"Full moves: {board.full_move}, Half moves (50 Move Rule): {board.half_move}")

        to_print = []
        for pos in range(64):
            x = Bitboard.get_x(pos)
            y = Bitboard.get_y(pos)

            color,piece_type = board.get(int(pos))

            output_str = " "
            if piece_type != None:
                output_str = PieceType.NUMBER_REPRESENTATIONS[piece_type]
                if color == PieceColor.WHITE: output_str = output_str.capitalize()

            to_print.append(output_str)

        BoardIO.print_square_values(to_print)

    @staticmethod
    def print_bitboard(bm:Bitboard):
        to_print = []

        for i in range(64):
            val = 1 if bm.occupied(i) else 0
            to_print.append(str(val))

        BoardIO.print_square_values(to_print)
        

    @staticmethod
    def __get_row_padding():
        output = "+"
        for i in range(8):
            output += "----+"
        return output

    @staticmethod
    def get_square_values(to_print:list):
        row_padding = BoardIO.__get_row_padding()
        output = ""

        for pos in range(64):
            if pos % 8 == 0:
                if pos != 0:
                    output += f"  {8 - Bitboard.get_y(pos - 1)} \n"
                output += row_padding + "\n"
                output += "|"
            
            output += f" {to_print[pos]}  |"

        output += "  1"
        output += "\n" + row_padding + "\n"
        output += ""


        for i in range(8):
            output += f"  {BoardIO.FILES_STR[i]}  "

        return output

    @staticmethod
    def print_square_values(to_print:list):
        print(BoardIO.get_square_values(to_print))

    @staticmethod
    def to_standard_coords(pos:int):
        x,y = Bitboard.get_pos_2d(pos)

        return f"{BoardIO.FILES_STR[x]}{8-y}"


    def print_move_array(arr:np.ndarray,piece_pos:int):
        length = Board.BOARDSQUARELENGTH
        output = np.zeros((length,length),dtype=str)
        output.fill(" ")
        for pos in arr:
            if pos == -1: break
            x = Bitboard.get_x(pos)
            y = Bitboard.get_y(pos)

            output[y,x] = str(1)
        
        x = Bitboard.get_x(piece_pos)
        y = Bitboard.get_y(piece_pos)  

        output[y,x] = "o"

        print(output)

def test():
    board = BoardIO.from_fen(FEN.START_POS)
    BoardIO.print_board(board)
    pass

def test_perf():
    board = BoardIO.from_fen(FEN.START_POS)

    t1 = time.perf_counter()
    track_perf = False
    if track_perf:
        pr = cProfile.Profile()
        pr.enable()

    for i in range(5000000):
        move_unmove(board)

    if track_perf:
        pr.disable()
        s = io.StringIO()
        sortby = SortKey.CUMULATIVE
        ps = pstats.Stats(pr,stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())

    t2 = time.perf_counter()

    print(t2 - t1)

    BoardIO.print_board(board)

    board.move(1,1+16-1,PieceColor.BLACK,piece_type=PieceType.KNIGHT,piece_type_to=PieceType.KNIGHT)

    BoardIO.print_board(board)

def move_unmove(board:Board):
    inst = board.move(1,1+16-1,PieceColor.BLACK,piece_type=PieceType.KNIGHT,piece_type_to=PieceType.KNIGHT)
    board.occupied(62-16+1)
    board.undo(inst)

def bitboard_test():
    bd = Bitboard(0)
    bd.toggle(0)
    oc = bd.occupied(0)

def fen_test():
    board = BoardIO.from_fen(FEN.START_POS)
    BoardIO.print_board(board)

def bitscan_test():
    t1 = time.perf_counter()
    num = 2**50

    show_perf = False
    pr = cProfile.Profile()
    pr.enable()

    for i in range(1000000):
        Bitboard.bitscan_forward(Bitboard(num + i))
    t2 = time.perf_counter()

    pr.disable()
    s = io.StringIO()
    sortby = SortKey.CUMULATIVE
    ps = pstats.Stats(pr,stream=s).sort_stats(sortby)
    ps.print_stats()
    print(s.getvalue())

    print(t2 - t1)

if __name__ == "__main__":
    fen_test()
