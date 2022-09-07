from typing import Callable
from board import *
from ctypes import c_uint64
from dataclasses import dataclass
import random


class MoveType:
    NORMAL = 1
    CASTLERIGHT = 2
    CASTLELEFT = 3
    ENPASSANT = 4
    PAWNFIRSTMOVE = 5
    PROMOTION = 6

    CASTLES = [CASTLELEFT,CASTLERIGHT]

class MoveCache(HashUtil):
    """
       A table driven move generation aproach is used to\n
       cache moves so they do not need to be recalculated on the fly.\n
       directions\n
       https://www.chessprogramming.org/Table-driven_Move_Generation#:~:text=Table%2Ddriven%20Move%20Generation%2C%20is,by%20piece%2Dtype%20and%20origin.\n
       Python list look ups are fast so why not use as many list look ups as possible?\n
       Not only are all moves cached in advanced, bitmasks of these possible moves are\n
       also cached for attacker detection in move legality test.\n
       Also included are maps / bitmasks for rows files, diagonals and "off diagonals".\n
       Diagonals are defined to go from sw to ne while "off diagonals" goes from south east to north west\n
       The 0th diagonal starts at position 0 (a8) and the 0th "off diagonal" starts at h8\n

       Now also provides hashes for zobrist hash\n
       https://www.chessprogramming.org/Zobrist_Hashing\n

       *************************************************************************************\n
        Quick direction lookup\n
       *************************************************************************************\n
       **********\n
        NW N NE                1 0 7    0      7   Black starts here\n
        W     E  Ordering:     2   6    \n
        SW S SE                3 4 5    56    63       White starts here\n
      ************\n
        \n
        [0,  1,  2,  3,  4,  5,  6,  7 ]      ['r' 'n' 'b' 'q' 'k' 'b' 'n' 'r']        BLACK\n
        [8,  9,  10, 11, 12, 13, 14, 15]      ['p' 'p' 'p' 'p' 'p' 'p' 'p' 'p']\n
        [16, 17, 18, 19, 20, 21, 22, 23]      [' ' ' ' ' ' ' ' ' ' ' ' ' ' ' ']\n
        [24, 25, 26, 27, 28, 29, 30, 31]      [' ' ' ' ' ' ' ' ' ' ' ' ' ' ' ']\n
        [32, 33, 34, 35, 36, 37, 38, 39]      [' ' ' ' ' ' ' ' ' ' ' ' ' ' ' ']\n
        [40, 41, 42, 43, 44, 45, 46, 47]      [' ' ' ' ' ' ' ' ' ' ' ' ' ' ' ']\n
        [48, 49, 50, 51, 52, 53, 54, 55]      ['P' 'P' 'P' 'P' 'P' 'P' 'P' 'P']\n
        [56, 57, 58, 59, 60, 61, 62, 63]      ['R' 'N' 'B' 'Q' 'K' 'B' 'N' 'R']         WHITE\n
    """

    """
    -----------------------------------------------
                    Move cache
    -----------------------------------------------
    """
    #Pawn moves are split up into moves and attacks
    moves_p_m_w:list[list[int]] = None
    moves_p_a_w:list[list[int]] = None
    moves_p_m_b:list[list[int]] = None
    moves_p_a_b:list[list[int]] = None
    
    #Moves for king and knight
    moves_k:list[list[int]] = None
    moves_n:list[list[int]] = None

    #Sliding moves for queens bishops and rooks
    moves_slide_n:list[list[int]] = None
    moves_slide_s:list[list[int]] = None
    moves_slide_w:list[list[int]] = None
    moves_slide_e:list[list[int]] = None
    moves_slide_ne:list[list[int]] = None
    moves_slide_nw:list[list[int]] = None
    moves_slide_sw:list[list[int]] = None
    moves_slide_se:list[list[int]] = None

    moves_direction_b:list[list[list[int]]] = None
    moves_direction_r:list[list[list[int]]] = None
    """
    -----------------------------------------------
    """

    """
    -----------------------------------------------
                    Bitmasks
    -----------------------------------------------
    """

    #Bitmasks for castling squares that need to be clear to castle
    castle_bitmasks:list[list[Bitboard]] = None

    #Bitmasks for ranks and files
    bitm_ranks:list[Bitboard] = None
    bitm_files:list[Bitboard] = None
    bitm_diag:list[Bitboard] = None
    bitm_off_diag:list[Bitboard] = None


    #Bitmasks for moves
    bitm_moves_p_a_w:list[Bitboard] = None
    bitm_moves_p_a_b:list[Bitboard] = None
    
    #Bitmasks for moves for king and knight
    bitm_moves_k:list[Bitboard] = None
    bitm_moves_n:list[Bitboard] = None

    #Bitmasks for sliding moves for queens bishops and rooks
    bitm_moves_slide_n:list[Bitboard] = None
    bitm_moves_slide_s:list[Bitboard] = None
    bitm_moves_slide_w:list[Bitboard] = None
    bitm_moves_slide_e:list[Bitboard] = None
    bitm_moves_slide_ne:list[Bitboard] = None
    bitm_moves_slide_nw:list[Bitboard] = None
    bitm_moves_slide_sw:list[Bitboard] = None
    bitm_moves_slide_se:list[Bitboard] = None

    bitm_squares_light:Bitboard = None
    bitm_squares_dark:Bitboard = None

    bitm_line_labels = None
    """
    Dictionary of bitmasks for ranks,files, diagonals and off diagonals. 
    Ranks - 0, files - 1, diagonals - 2, off - diagonals - 3 
    """

    """
    -----------------------------------------------
    """

    
    """
    -----------------------------------------------
                    Maps
    -----------------------------------------------
    """
    #Rook positions castling diretion
    castle_directions:list[list[Bitboard]] = None

    map_file:list = None
    """Collumns (vertical)"""
    map_ranks:list = None
    """Rows (horizontal)"""
    map_diagonals:list = None
    """Diagonals are defined to go from southwest to northeast 0th diagonal starts at 0"""
    map_off_diagonals:list = None
    """Off diagonals are defined to go from northwest to southeast 0th diagonal starts at 56th square"""


    map_line_labels = None
    """
    Dictionary of labels for ranks,files, diagonals and off diagonals. 
    Ranks - 0, files - 1, diagonals - 2, off - diagonals - 3 
    """

    """
    -----------------------------------------------
    """


    """
    -----------------------------------------------
                    Hashes
    -----------------------------------------------
    Hashes for Zobrist hashing function 
    https://en.wikipedia.org/wiki/Zobrist_hashing
    """
    hashes_white_pieces:list[list[int]] = None
    hashes_black_pieces:list[list[int]] = None
    hashes_castling_rights:list[int] = None
    hashes_enpassant_target:list[int] = None
    hashes_turn:int = None

    """
    -----------------------------------------------
    """


    def __init_arrays(self):
        self.moves_p_m_w = []
        self.moves_p_a_w = []
        self.moves_p_m_b = []
        self.moves_p_a_b = []


        self.moves_n = []
        self.moves_k = []

        self.moves_slide_n = []
        self.moves_slide_s = []
        self.moves_slide_w = []
        self.moves_slide_e = []
        self.moves_slide_ne = []
        self.moves_slide_nw = []
        self.moves_slide_sw = []
        self.moves_slide_se = []
        
        self.moves_direction_b= []
        self.moves_direction_r = []

        self.castle_directions = []
        self.castle_bitmasks = []

        self.map_ranks = []
        self.map_file = []
        self.map_diagonals = []
        self.map_off_diagonals = []

        self.bitm_line_labels = None
        self.map_line_labels = None

        self.bitm_moves_p_a_w = []
        self.bitm_moves_p_a_b = []

        #Bitmasks for moves for king and knight
        self.bitm_moves_k = []
        self.bitm_moves_n = []

        #Bitmasks for sliding moves for queens bishops and rooks
        self.bitm_moves_slide_n = []
        self.bitm_moves_slide_s = []
        self.bitm_moves_slide_w = []
        self.bitm_moves_slide_e = []
        self.bitm_moves_slide_ne = []
        self.bitm_moves_slide_nw = []
        self.bitm_moves_slide_sw = []
        self.bitm_moves_slide_se = []

    def __gen_sliding_moves(self,pos):
        """Generates all sliding moves for the position"""
        self.moves_slide_n.append(PrePseudoMoves.get_slide_moves(pos,(0,-1)))
        self.moves_slide_s.append(PrePseudoMoves.get_slide_moves(pos,(0,1)))
        self.moves_slide_w.append(PrePseudoMoves.get_slide_moves(pos,(-1,0)))
        self.moves_slide_e.append(PrePseudoMoves.get_slide_moves(pos,(1,0)))
        self.moves_slide_ne.append(PrePseudoMoves.get_slide_moves(pos,(1,-1)))
        self.moves_slide_nw.append(PrePseudoMoves.get_slide_moves(pos,(-1,-1)))
        self.moves_slide_sw.append(PrePseudoMoves.get_slide_moves(pos,(-1,1)))
        self.moves_slide_se.append(PrePseudoMoves.get_slide_moves(pos,(1,1)))
            

    def __gen_piece_moves(self):
        """Populates our arrays with possible moves"""
        for pos in range(64):
            self.moves_n.append(PrePseudoMoves.moves_knight(pos))
            self.moves_p_m_w.append(PrePseudoMoves.moves_pawn(pos,PieceColor.WHITE))
            self.moves_p_m_b.append(PrePseudoMoves.moves_pawn(pos,PieceColor.BLACK))
            self.moves_p_a_w.append(PrePseudoMoves.attacks_pawn(pos,PieceColor.WHITE))
            self.moves_p_a_b.append(PrePseudoMoves.attacks_pawn(pos,PieceColor.BLACK))

            self.moves_k.append(PrePseudoMoves.moves_king(pos))
            self.__gen_sliding_moves(pos)


            self.moves_direction_r = [
                self.moves_slide_n,
                self.moves_slide_w,
                self.moves_slide_s,
                self.moves_slide_e
            ]

            self.moves_direction_b = [
                self.moves_slide_nw,
                self.moves_slide_sw,
                self.moves_slide_se,
                self.moves_slide_ne

            ]

    def __init_castle_masks(self) -> None:
        """Initialize bitmasks to check for clear squares when castling"""
        #These are the squares that need to be cleared to castle
        bm_castle_w_w, bm_castle_w_e = Bitboard(),Bitboard()
        bm_castle_b_w, bm_castle_b_e = Bitboard(),Bitboard()

        bm_castle_b_w.set(1)
        bm_castle_b_w.set(2)
        bm_castle_b_w.set(3)

        bm_castle_b_e.set(6)
        bm_castle_b_e.set(5)
    
        #Black and white castles are the same but shifted to other side of board
        bm_castle_w_e.value = bm_castle_b_e.value << 7*8
        bm_castle_w_w.value = bm_castle_b_w.value << 7*8




        self.castle_bitmasks = [
            [bm_castle_w_w,bm_castle_w_e],
            [bm_castle_b_w,bm_castle_b_e]
        ]

    def init_ranks_files(self):
        for i in range(64):
            self.map_file.append(i % 8)
            self.map_ranks.append(i // 8)

            x,y = Bitboard.get_pos_2d(i)

            self.map_diagonals.append(x + y)
            self.map_off_diagonals.append((7-x) + y)

        self.map_line_labels = [self.map_ranks,self.map_file,self.map_diagonals,self.map_off_diagonals]
            


    def __init_castle_directions(self):
        self.castle_directions = [
            [56,63], #Default rook positions white
            [0,7]    #Default rook positions black
        ]

    def __init_misc(self):
        self.__init_castle_directions()

    def __init_maps(self):
        self.init_ranks_files()

    def __map_to_mask(self, map:list[int],masks:list[Bitboard]):
        """Converts a map into a list of bitmasks"""
        for pos,map_val in enumerate(map):
            masks[map_val].set(pos)

    def __move_map_to_mask(self,maps:list[list[int]],masks:list[Bitboard]) -> None:
        for i in range(64):
            masks.append(Bitboard())
        
        for pos,map in enumerate(maps):
            c_mask = masks[pos]
            for attack in map:
                c_mask.set(attack)
            

    def __init_square_bit_maps(self):
        #8 ranks / files
        self.bitm_ranks = [Bitboard() for i in range(8)]
        self.bitm_files = [Bitboard() for i in range(8)]

        #15 diagonals / off diagonalis on board on board
        self.bitm_diag = [Bitboard() for i in range(15)]
        self.bitm_off_diag = [Bitboard() for i in range(15)]

        #Turn the maps of ranks, etc into bitmasks
        self.__map_to_mask(self.map_ranks,self.bitm_ranks)
        self.__map_to_mask(self.map_file,self.bitm_files)
        self.__map_to_mask(self.map_diagonals,self.bitm_diag)
        self.__map_to_mask(self.map_off_diagonals,self.bitm_off_diag)

        self.bitm_line_labels = [self.bitm_ranks,self.bitm_files,self.map_diagonals,self.bitm_off_diag]

    def __init_move_bit_masks(self):
        self.__move_map_to_mask(self.moves_n,self.bitm_moves_n)

        self.__move_map_to_mask(self.moves_k,self.bitm_moves_k)

        self.__move_map_to_mask(self.moves_p_a_w,self.bitm_moves_p_a_w)
        self.__move_map_to_mask(self.moves_p_a_b,self.bitm_moves_p_a_b)


        self.__move_map_to_mask(self.moves_slide_n,self.bitm_moves_slide_n)
        self.__move_map_to_mask(self.moves_slide_s,self.bitm_moves_slide_s)
        self.__move_map_to_mask(self.moves_slide_w,self.bitm_moves_slide_w)
        self.__move_map_to_mask(self.moves_slide_e,self.bitm_moves_slide_e)

        self.__move_map_to_mask(self.moves_slide_nw,self.bitm_moves_slide_nw)
        self.__move_map_to_mask(self.moves_slide_ne,self.bitm_moves_slide_ne)
        self.__move_map_to_mask(self.moves_slide_se,self.bitm_moves_slide_se)
        self.__move_map_to_mask(self.moves_slide_sw,self.bitm_moves_slide_sw)
    
    def __init_color_masks(self):
        light_squares = Bitboard()
        dark_squares = Bitboard()

        for i in range(64):
            if i % 2 == 0:
                light_squares.set(i)
            else:
                dark_squares.set(i)

        self.bitm_squares_light = light_squares
        self.bitm_squares_dark = dark_squares
        

    def __init_bit_masks(self):
        self.__init_castle_masks()
        self.__init_square_bit_maps()
        self.__init_move_bit_masks()
        self.__init_color_masks()


    def __init_hash(self):
        random.seed = 8293449743051711766
        len_hash = 2**64
        #Generate random for numbers for hashed pieces
        self.hashes_white_pieces = [[c_uint64(random.randrange(0,len_hash)).value for pos in range(64)] for piece_type in range(6)]
        self.hashes_black_pieces = [[c_uint64(random.randrange(0,len_hash)).value for pos in range(64)] for piece_type in range(6)]
        self.hashes_castling_rights = [c_uint64(random.randrange(0,len_hash)).value for castle_right in range(16)]
        self.hashes_enpassant_target = [c_uint64(random.randrange(0,len_hash)).value for file in range(8)]
        self.hashes_turn = c_uint64(random.randrange(0,len_hash)).value


    def get_hash_turn(self,turn: int)->int:
        """Hashes for turn, if it is black's turn return hash for black turn otherwise return None"""
        if turn == PieceColor.BLACK:
            return self.hashes_turn

    def get_hash_piece(self,piece_type: int, square: int, color: int)->int:
        if color == PieceColor.WHITE:
            return self.hashes_white_pieces[piece_type][square]
        else:
            return self.hashes_black_pieces[piece_type][square]

    def get_hash_castling_rights(self,castle_rights:CastleRights)->int:
        return self.hashes_castling_rights[castle_rights.value]

    def get_hash_enpassant(self,target:int)->int:
        file = self.map_file[target]
        return self.hashes_enpassant_target[file]

    def __init__(self) -> None:
        self.__init_arrays()
        self.__gen_piece_moves()
        self.__init_misc()
        self.__init_maps()
        self.__init_bit_masks()
        self.__init_hash()
        



    

class PrePseudoMoves:
    """Creates pre-pseudo legal moves for the move cache"""

    #Attacking directions for the pieces
    ROOK_ATTACK_DIRECTIONS = [(-1,0),(1,0),(0,-1),(0,1)]
    BISHOP_ATTACK_DIRECTIONS = [(1,1),(1,-1),(-1,1),(-1,-1)]
    KNIGHT_ATTACK_DIRECTIONS = [(-2,-1),(-2,1),(2,-1),(2,1),(-1,-2),(-1,2),(1,-2),(1,2)]
    ROYAL_ATTACK_DIRECTIONS = BISHOP_ATTACK_DIRECTIONS + ROOK_ATTACK_DIRECTIONS


    @staticmethod
    def __add_move(moves:list[int],pos:int,direction:tuple[int,int])->bool:
        """Checks if move is on board, if it is adds it to list of moves"""
        move = Bitboard.shift_check(pos,direction)
        if move == None: return False

        moves.append(move)
        return True

    @staticmethod
    def moves_knight(pos):
        moves = []

        for attack in PrePseudoMoves.KNIGHT_ATTACK_DIRECTIONS:
            PrePseudoMoves.__add_move(moves,pos,attack)
        
        return moves

    @staticmethod
    def moves_pawn(pos,color):
        dir = -1 if color == PieceColor.WHITE else 1

        #No pawn moves if we are on either y end of the board. How did we get here in the first places
        y = Bitboard.get_y(pos)
        if y == 0 or y == 7: return []

        moves = []

        #Basic move / attack moves
        PrePseudoMoves.__add_move(moves,pos,(0,dir))

        #First move
        if (y == 6 and color == PieceColor.WHITE) or (y == 1 and color == PieceColor.BLACK):
            PrePseudoMoves.__add_move(moves,pos,(0,2*dir))

        return moves

    def attacks_pawn(pos,color):
        dir = -1 if color == PieceColor.WHITE else 1

        #No pawn moves if we are on either y end of the board. How did we get here in the first places
        y = Bitboard.get_y(pos)
        #if y == 0 or y == 7: return []

        moves = []

        PrePseudoMoves.__add_move(moves,pos,(-1,dir))
        PrePseudoMoves.__add_move(moves,pos,(1,dir))

        return moves

    @staticmethod
    def moves_king(pos):
        moves = []

        for dir in PrePseudoMoves.ROYAL_ATTACK_DIRECTIONS:
            PrePseudoMoves.__add_move(moves,pos,dir)

        return moves

    @staticmethod
    def get_slide_moves(pos:int,dir:tuple[int,int]):
        moves = []

        c_x = Bitboard.get_x(pos)
        c_y = Bitboard.get_y(pos)
        #Continue generating sliding moves until we hit edge of board
        while(1):
            c_pos = Bitboard.get_pos(c_x,c_y)
            if not PrePseudoMoves.__add_move(moves,c_pos,dir): break
            c_x += dir[0]
            c_y += dir[1]

        return moves

def perf_test():
    from math import log
    t1 = time.perf_counter()

    for i in range(1000000):
        log(i+1,2)

    t2 = time.perf_counter()
    print(t2 - t1)

def test():
    cache = MoveCache()
    #BoardIO.print_square_values(cache.map_off_diagonals)
    BoardIO.print_square_values(cache.map_diagonals)
    BoardIO.print_square_values(cache.map_off_diagonals)

if __name__ == "__main__":
    test()


