from math import sqrt,ceil
from moveengine import *
import chess

class PST:
    """Piece square tables from https://www.chessprogramming.org/Simplified_Evaluation_Function """
    
    PW = [ 
            0,  0,  0,  0,  0,  0,  0,  0,
            50, 50, 50, 50, 50, 50, 50, 50,
            10, 10, 20, 30, 30, 20, 10, 10,
             5,  5, 10, 25, 25, 10,  5,  5,
             0,  0,  0, 20, 20,  0,  0,  0,
             5, -5,-10,  0,  0,-10, -5,  5,
             5, 10, 10,-20,-20, 10, 10,  5,
             0,  0,  0,  0,  0,  0,  0,  0
        ]
    
    PW_END = [ 
            0,  0,  0,  0,  0,  0,  0,  0,
            100, 100, 75, 75, 75, 75, 100, 100,
            75, 75, 50, 50, 50, 50, 75, 75,
             25,  25,   0,    0,  0,   0,  25,  25,
             30,  30,  -25, -25, -25, -25, 30, 30,
             10,  10,  -50, -50, -50, -50, 10,  10,
             -75, -75, -75, -75,-75, -75, -75,  -75,
             0,  0,  0,  0,  0,  0,  0,  0
        ]

    NW = [
            -50,-40,-30,-30,-30,-30,-40,-50,
            -40,-20,  0,  0,  0,  0,-20,-40,
            -30,  0, 10, 15, 15, 10,  0,-30,
            -30,  5, 15, 20, 20, 15,  5,-30,
            -30,  0, 15, 20, 20, 15,  0,-30,
            -30,  5, 10, 15, 15, 10,  5,-30,
            -40,-20,  0,  5,  5,  0,-20,-40,
            -50,-40,-30,-30,-30,-30,-40,-50
        ]

    BW = [
            -20,-10,-10,-10,-10,-10,-10,-20,
            -10,  0,  0,  0,  0,  0,  0,-10,
            -10,  0,  5, 10, 10,  5,  0,-10,
            -10,  5,  5, 10, 10,  5,  5,-10,
            -10,  0, 10, 10, 10, 10,  0,-10,
            -10, 10, 10, 10, 10, 10, 10,-10,
            -10,  5,  0,  0,  0,  0,  5,-10,
            -20,-10,-10,-10,-10,-10,-10,-20
        ]

    RW = [   
             0,  0,  0,  0,  0,  0,  0,  0,
             5, 10, 10, 10, 10, 10, 10,  5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
             0,  0,  0,  5,  5,  0,  0,  0
    ]

    QW = [
            -20,-10,-10, -5, -5,-10,-10,-20,
            -10,  0,  0,  0,  0,  0,  0,-10,
            -10,  0,  5,  5,  5,  5,  0,-10,
             -5,  0,  5,  5,  5,  5,  0, -5,
              0,  0,  5,  5,  5,  5,  0, -5,
            -10,  5,  5,  5,  5,  5,  0,-10,
            -10,  0,  5,  0,  0,  0,  0,-10,
            -20,-10,-10, -5, -5,-10,-10,-20
    ]

    KW_MIDDLE = [
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
         20, 20,  0,  0,  0,  0, 20, 20,
         20, 30, 10,  0,  0, 10, 30, 20
    ]


    KW_END = [
        -50,-40,-30,-20,-20,-30,-40,-50,
        -30,-20,-10,  0,  0,-10,-20,-30,
        -30,-10, 20, 30, 30, 20,-10,-30,
        -30,-10, 30, 40, 40, 30,-10,-30,
        -30,-10, 30, 40, 40, 30,-10,-30,
        -30,-10, 20, 30, 30, 20,-10,-30,
        -30,-30,  0,  0,  0,  0,-30,-30,
        -50,-30,-30,-30,-30,-30,-30,-50
    ]

    PB = list(reversed(PW))
    PB_END = list(reversed(PW_END))
    NB = list(reversed(NW))
    BB = list(reversed(BW))
    RB = list(reversed(RW))
    QB = list(reversed(QW))


    KB_MIDDLE = list(reversed(KW_MIDDLE))
    KB_END = list(reversed(KW_END))

    #Eventually it may be wise to add more precise tables for middle and end games
    TABLES_MIDDLE = (
        (
            PW,
            NW,
            BW,
            RW,
            QW,
            KW_MIDDLE
        ),
        (
            PB,
            NB,
            BB,
            RB,
            QB,
            KB_MIDDLE
        )
    )

    TABLES_END = (
        (
            PW_END,
            NW,
            BW,
            RW,
            QW,
            KW_END
        ),
        (
            PB_END,
            NB,
            BB,
            RB,
            QB,
            KB_END
        )
    )

    @staticmethod
    def get_table(color,piece_type,endgame:bool):
        if endgame: return PST.TABLES_END[color][piece_type]
        return PST.TABLES_MIDDLE[color][piece_type]

class Evaluation:
    PIECE_WIEGHTS_BASIC = {PieceType.PAWN: 100, PieceType.KNIGHT:320, PieceType.BISHOP:330, PieceType.ROOK:500, PieceType.QUEEN:900}
    PIECE_WIEGHTS_BASIC_KING = {PieceType.PAWN: 100, PieceType.KNIGHT:320, PieceType.BISHOP:330, PieceType.ROOK:500, PieceType.QUEEN:900,PieceType.KING:10000}
    """Piece weights in centi pawns - https://www.chessprogramming.org/Simplified_Evaluation_Function """
    WEIGHT_CHECKMATE = 100000
    FANCY = True
    """If false evaluations use only basic wieghts and piece square tables. If true more advanced metrics are included"""

    @staticmethod
    def evaluate(me:MoveEngine,alpha:int,beta:int,first_quiet:bool,_endgame:bool):
        """Evaluates static position, symetric sign IE if it is white's positive score is winning for white if black's turn positive score is winning for black"""
        coef = 1 if me.turn == PieceColor.WHITE else -1

        #In future implement delta pruning
        eval = 0

        eval += Evaluation.evaluation_material_basic(me,first_quiet,_endgame)
        eval += Evaluation.eval_positions_basic(me,_endgame)
        eval += Evaluation.eval_king_saftey_basic(me,_endgame)

        return coef*eval


    def is_endgame(me:MoveEngine):
        """
        Endgame begins when both either sides have no queen and no more than 3 lesser pieces (rook bishop knight) or a queen and no more than 1 lesser piece
        #Need better definition in future because of promotions
        https://www.chessprogramming.org/Simplified_Evaluation_Function
        """
        #TODO implement
        board = me.board
        for color in range(2):
            knights = board.get_piece_count(color,PieceType.KNIGHT)
            bishops = board.get_piece_count(color,PieceType.BISHOP)
            rooks = board.get_piece_count(color,PieceType.ROOK)
            queens = board.get_piece_count(color,PieceType.QUEEN)

            lesser_piece_count = knights + bishops + rooks
            
            if lesser_piece_count < 3 and queens == 0: return True
            if queens > 0 and lesser_piece_count < 1: return True

        return False

    @staticmethod
    def eval_positions_basic(me:MoveEngine,is_endgame:bool):
        """Uses Piece Square Tables to quickly evaluate the positions of pieces"""
        #Choose different tables based on wether we are in endagme or not
        board = me.board
        
        eval = 0
        for piece_color in range(2):
            for piece_type in range(6):
                for piece_pos in board.get_locations_piece(piece_color,piece_type):
                    dir = 1 if piece_color == PieceColor.WHITE else -1
                    tbl = PST.get_table(piece_color,piece_type,is_endgame)
                    eval += dir * tbl[piece_pos]

        return eval
    
    def __get_weight_piece(me:MoveEngine,piece_type:int, a_pawn_count:int, piece_count:int, color:int,board:Board)->int:
        """
        Returns the weight of the piece. If fancy evaluation is turned on piece wieght may be adjusted by factors such as pawn count
        pawn color ocupancy,...
        """
        adj_weight = Evaluation.PIECE_WIEGHTS_BASIC[piece_type]
        #If fancy evaluation is turned off simply return the basic weight of the piece
        if not Evaluation.FANCY: return adj_weight

        #Apply weight to knight based on how many oposing pawns are on board
        if piece_type == PieceType.KNIGHT:
            adj_weight += -5 * (8 - a_pawn_count)
        #Adjust bishop weight depending on the number of pawns on light / dark squares
        if piece_type == PieceType.BISHOP and piece_count == 1:
            pawn_board = board.get_board_piece(PieceColor.WHITE,PieceType.PAWN).value | board.get_board_piece(PieceColor.BLACK,PieceType.PAWN).value
            loc = board.get_locations_piece(color,PieceType.BISHOP)[0]
            
            if me.cache.bitm_squares_light.occupied(loc):
                #Dark square bishop
                #Darksquare bishops decrease in power with more light square pawns
                light_pawn_count = Bitboard.popcount(Bitboard(pawn_board & me.cache.bitm_squares_light.value))
                adj_weight +=  -5 * (8 - light_pawn_count)
            else:
                #Light square bishop
                #Lightsquare bishop decrease in power with more dark square pawns
                dark_pawn_count = Bitboard.popcount(Bitboard(pawn_board & me.cache.bitm_squares_dark.value))
                adj_weight += -5 * (8 - dark_pawn_count)
            #Bishops increase in power as pawns disapear off board
            adj_weight += 6 * (8-a_pawn_count)
        
        return adj_weight

    @staticmethod
    def __get_material_coef(color_eval:list[int]):
        """
        Returns a coeficient to multiply the material score by. 
        Coeficient is ratio of the two side's material with king included such that the winning side gets a bonus. \n
        color eval - list of lists of piece evaluations in format
        """
        #If fancy evaluation is turned off return a ratio of 1
        if not Evaluation.FANCY: return 1

        color_eval_w = sum(color_eval[PieceColor.WHITE]) + 10000
        color_eval_b = sum(color_eval[PieceColor.BLACK]) + 10000

        assert color_eval_w >= 0 and color_eval_b >= 0

        ratio = 1
        if color_eval_w > color_eval_b:
            ratio = color_eval_w/color_eval_b
        else:
            ratio = color_eval_b/color_eval_w

        return ratio


    @staticmethod
    def evaluation_material_basic(me:MoveEngine,first_quiet:bool,is_endgame:bool)->int:
        """Evaluates the difference in material wieghts for both sides, positive means more material for white, negative more material for black"""
        material = []
        board = me.board

        if first_quiet and me.in_checkmate():
            return -Evaluation.WEIGHT_CHECKMATE if board.turn == PieceColor.WHITE else Evaluation.WEIGHT_CHECKMATE

        color_eval = [[],[]]

        #Get evaluation for black and white pieces
        for color in range(2):

            #Number of pawns on other side, used for knight and bishop evaluation
            a_pawn_count = len(board.get_locations_piece(PieceColor.reverse_color(color),PieceType.PAWN))

            dir = 1 if color == PieceColor.WHITE else -1

            #Loop throught piece types
            for piece_type in Evaluation.PIECE_WIEGHTS_BASIC:
                #Get the weight, multiply it by the number of pieces of given type, and add it to list
                piece_count = board.get_piece_count(color,piece_type)
                weight = Evaluation.__get_weight_piece(me,piece_type,a_pawn_count,piece_count,color,board)
                valuation = piece_count * weight
                material.append(dir*valuation)
                color_eval[color].append(valuation)

        
        #Maximum multiplier of 1.49
        ratio = Evaluation.__get_material_coef(color_eval)

        return int(sum(material) * ratio)


    @staticmethod
    def eval_king_saftey_basic(me:MoveEngine,is_endgame = False):
        """
        Evaluates pawn saftey around king.
        Implementation - Check for atleast one pawn in front of king
        """

        #TODO move anything to do with pawns into a pawn evaluation function
        board = me.board
        cache = me.cache

        eval = 0

        #If fancy evaluation is turned off return 0
        if not Evaluation.FANCY: return 0

        #Heavy penalty for not having pawn in front of king when enemy has sliding attackers on board .  
        for color in range(2):

            dir = 1 if color == PieceColor.WHITE else -1

            #Penalty for allowing pieces behind king

            king_pos = me.get_king_pos(color)
            king_rank = cache.map_ranks[king_pos]
            attacker_color = PieceColor.reverse_color(color)
            for piece_type in [PieceType.ROOK,PieceType.QUEEN]:
                for location in board.get_locations_piece(attacker_color,piece_type):
                    rank = cache.map_ranks[location]
                    if color == PieceColor.WHITE and rank <= king_rank + 1:
                        eval += dir * 10
                    if color == PieceColor.BLACK and rank >= king_rank - 1:
                        eval += dir * 10



            if not is_endgame:            
                #Penalty for no pawn sheild
                slider_count = sum([board.get_piece_count(attacker_color,piece_type) for piece_type in PieceType.SLIDING_PIECES])
                mask = cache.bitm_moves_slide_n[king_pos] if color == PieceColor.WHITE else cache.bitm_moves_slide_s[king_pos]
                mask2 = cache.bitm_moves_p_a_w[king_pos] if color == PieceColor.WHITE else cache.bitm_moves_p_a_b[king_pos]
                pawn_board = board.get_board_piece(color,PieceType.PAWN)
                if ((mask.value & pawn_board.value) == 0) and ((mask2.value & pawn_board.value) == 0):
                    eval += -5 * abs((slider_count - 1)) * dir
            else:
                #Add bonus for keeping king close to pawns
                king_file = cache.map_file[king_pos]


                for pawn_color in range(2):
                    pawn_positions = board.get_locations_piece(pawn_color,PieceType.PAWN)
                    for pawn_pos in pawn_positions:
                        pawn_rank = cache.map_ranks[pawn_pos]
                        pawn_file = cache.map_file[pawn_pos]

                        dist = sqrt((pawn_rank-king_rank)**2 + (pawn_file-king_file)**2)
                        eval += ceil((8 - dist)/4)

                

        return eval
        


