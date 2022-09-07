from pseudomoves import *
from hashing import ChessHashing
from typing import Any
import operator

class PinType:
    NORMAL = 0
    ENPASSANT = 1

class TerminalStatus:
    NotTerminal = 0
    Checkmate = 1
    Stalemate = 2
    Draw = 3

class MoveEngine:
    __legal_mode:bool = False

    board:Board = None
    cache:MoveCache = None

    can_draw:bool = True

    checkers_record:list[tuple[int,int]] = None
    instruction_stack:list[MoveInstruction] = None
    move_stack:list[Move] = None

    #Hashed positions with number of time position has been visited
    reached_positions:list[int]= None

    allow_null:bool = False

    @property
    def current_hash(self)->int:
        return self.reached_positions[-1]

    @property
    def checkers(self)->list[tuple[int,int]]:
        return self.checkers_record[-1]

    @property
    def in_check(self)->bool:
        return len(self.checkers) > 0

    @property
    def turn(self)->int:
        return self.board.turn

    class LegalModeException(Exception):
        """Exception to raise when there is an issue legal mode """
        def __init__(self, movestack:list[Move], msg:str) -> None:
            self.movestack = movestack
            super().__init__(msg)

    @property
    def legal_mode(self)->bool:
        """
        Sets wether the board is in legal mode or not. 
        If legal mode is active, pushing a move that captures king is not allowed.
        Aditionaly, if legal mode is active pushing a null move when king is in check is not allowed.
        If legal mode is disabled, any functions that evaluate move legality 
        or test for pins are raise exceptions
        """
        return self.__legal_mode

    @legal_mode.setter
    def legal_mode(self,value:bool):
        #We may always switch legal mode off
        if not value: 
            self.__legal_mode = value
            return

        #Ensure we have exactly one king on both sides before switching legal mode on
        king_count_w = self.board.get_piece_count(PieceColor.WHITE,PieceType.KING)
        king_count_b = self.board.get_piece_count(PieceColor.BLACK,PieceType.KING)

        if king_count_w != 1 or king_count_b != 1:
            raise self.__legal_exception("May not switch into legal mode if both sides do not have king")

        self.__legal_mode = value

    def __legal_exception(self,msg:str)->LegalModeException:
        output = f"""
         Exception occoured with MoveEngine in legal mode.
         Message: {msg}
         Movestack: {self.move_stack} 
         """
        return self.LegalModeException(self.move_stack,output)

    def get_king_pos(self,color):
        """Gets position of king for specified piece color, raises Exception if called when not in legal mode"""
        if not self.__legal_mode:
            raise self.__legal_exception("King position not guaranteed when not in legal mode")

        return self.board.get_locations_piece(color,PieceType.KING)[0]

    def __get_piece_rank_file(self,pos:int)->tuple[int,int]:
        return (self.cache.map_ranks[pos], self.cache.map_file[pos])

    def __get_piece_diag_off_diag(self,pos)->tuple[int,int]:
        return (self.cache.map_diagonals[pos],self.cache.map_off_diagonals[pos])


    def __mask_scan(self,bb:Bitboard,bitm:Bitboard,forward:bool)->int:
        """
        Applies a mask to given bitboard. If this is 0 returns None otherwise performs 
        the requested bitscan (either forward or reverse) and returns value
        """
        masked = Bitboard(bb.value & bitm.value)
        if masked.value == 0: return None
        if forward: return Bitboard.bitscan_forward(masked)
        return Bitboard.bitscan_reverse(masked)

    def __pin_mask_scan(self,bb:Bitboard,bitm:Bitboard,king_pos:int,attacker_pos:int):
        """
        Used to scan for pins on king.
        Returns index of pinned piece
        Note currently includes enemy pieces as pinned targets.
        This is ok for now
        """

        #Apply line mask and mask out anything behind king

        #Mask out everything behind king with shift mask
        if king_pos > attacker_pos:
            shift_mask = ~(bitm.value << (king_pos - attacker_pos))
        else:
            shift_mask = ~(bitm.value >> (attacker_pos - king_pos))

        #Now apply both masks to get just the the king and it's defenders
        masked = Bitboard((bb.value & bitm.value) & shift_mask)


        #Line mask does not include attacker so if we remove king only the pieces in the way remain
        #Remove king
        masked.unset(king_pos)

        #King must be in check if we have 0 here, return none because no piece is pinned just king in check
        if masked.value == 0: return None

        #Scan and get piece in the way
        #Can use bitscan forward or reverse, doesn't matter 
        #Currently, bitscan reverse is faster so use bitscan reverse
        hit1 = Bitboard.bitscan_reverse(masked)
        
        #Remove piece
        masked.unset(hit1)


        # Now that this "defender" is removed if we are pinned no pieces are in the way
        # Therefore our mask value is 0 if we are pinned
        if masked.value == 0: return hit1


        return None

    
    
    def __pin_scan(self,line_type:int,king_pos:int,attacker_pos:int,attacker_line_position:int)->tuple[int,int,int,int]:
        """
        Scans for pins. Returns a tuple in the following format\n
        (pinned piece position, pinned line type, pinned line position, pintype)\n
        pinned line type - 0 for ranks, 1 for files, 2 for diagonals 3 for off diagonals\n
        pinned line position - the number coresponding to the ranks/file/diagonal/..
        the piece is pinned to. More info in MoveCache class.\n
        PinType - 0 for normal pins 1 for pins preventing enpassant
        """
        assert line_type >= 0 and line_type < 4

        cache = self.cache

        bitm_attack = None
        if line_type == 0:
            #Look at ranks
            #If king pos is greater than the attacker position the king is to the east
            if king_pos > attacker_pos:
                bitm_attack = cache.bitm_moves_slide_e[attacker_pos]
            else:
                bitm_attack = cache.bitm_moves_slide_w[attacker_pos]
        elif line_type == 1:
            #Looking at files
            #If king pos is greater than the attacker position the king is to the south
            if king_pos > attacker_pos:
                bitm_attack = cache.bitm_moves_slide_s[attacker_pos]
            else:
                bitm_attack = cache.bitm_moves_slide_n[attacker_pos]
        elif line_type == 2:
            #looking at diagonals
            #Diagonals go from sw to ne
            #If king pos is greater than attacker position the king is to the south west
            if king_pos > attacker_pos:
                bitm_attack = cache.bitm_moves_slide_sw[attacker_pos]
            else:
                bitm_attack = cache.bitm_moves_slide_ne[attacker_pos]
        else: 
            #Looking at anti diagonals
            #Anti diagonals go from se to nw
            #If king pos is greater than attacker position the king is to the south east
            if king_pos > attacker_pos:
                bitm_attack = cache.bitm_moves_slide_se[attacker_pos]
            else:
                bitm_attack = cache.bitm_moves_slide_nw[attacker_pos]
        
        #Finnaly do our pin scan
        scan_result = self.__pin_mask_scan(self.board.squares,bitm_attack,king_pos,attacker_pos)

        #Record pin information
        pin_info = (scan_result,line_type,attacker_line_position,PinType.NORMAL)

        #Special case enpassant horizontal pin
        #Special case cannot happen for pins that are not rank pins
        #If there is no enpassant target
        #Or if we already found a pin
        if line_type != 0 or self.board.enpassant_target == None or scan_result != None:
            return pin_info
            
        #Check if we are on same rank as enpassant target
        rank_ep = cache.map_ranks[self.board.enpassant_target]
        
        if rank_ep != attacker_line_position:
            return pin_info

        #Ok we have possible enpassant pin case
        #we must rescan with but with enpassant target removed
        squares_target_removed = Bitboard(self.board.squares.value)
        squares_target_removed.unset(self.board.enpassant_target)

        scan_result2 = self.__pin_mask_scan(squares_target_removed,bitm_attack,king_pos,attacker_pos)
        
        if scan_result2 == None:
            return pin_info
        
        #Ensure the pinned piece is a pawn
        pawn_board = self.board.get_board_piece(self.turn,PieceType.PAWN)
        if not pawn_board.occupied(scan_result2):
            return pin_info

        #Ensure the pawn can capture enpassant
        if (not self.board.enpassant_target + 1 == scan_result2) and (not self.board.enpassant_target - 1 == scan_result2):
            return pin_info

        #Ok we have special case, report pin as a pin in the vertical direction
        #so our pawn may not capture enpassant
        return (scan_result2,0,attacker_line_position,PinType.ENPASSANT)

            
        

    def __get_pins_rook(self,kingpos,rook_locations,king_rank,king_file):
        """
        Loops throught provided rooks positions, finds pins. Returns a list of pins in format: \n
        (pinned piece, pinned line type (2 for diagonals, 3 for off diagonals) , (diagonal positon (1 - 14))) \n
        For more information on diagonal position see move cache \n
        """
        pin_list:list[tuple[int,int]] = []

        #TODO need to add in code to fix "enpassant bug"

        for rook_pos in rook_locations:
            rook_rank,rook_file = self.__get_piece_rank_file(rook_pos) 
            
            if rook_rank == king_rank:
                pin = self.__pin_scan(0,kingpos,rook_pos,rook_rank)
                if pin[0] != None: pin_list.append(pin)
            
            elif rook_file == king_file:
                pin = self.__pin_scan(1,kingpos,rook_pos,rook_file)
                if pin[0] != None: pin_list.append(pin)
        return pin_list

    def __get_pins_bishop(self,kingpos,bishop_locations,king_diagonal,king_off_diagonal):
        """
        Loops throught provided bishop positions, finds pins. Returns a list of pins in format: \n
        (pinned piece, pinned line type (2 for diagonals, 3 for off diagonals) , (diagonal positon (1 - 14))) \n
        For more information on diagonal position see move cache \n
        """
        pin_list:list[tuple[int,int]] = []

        for bishop_pos in bishop_locations:
            #look up the bishop diagonal and off diagonal
            bishop_diag,bishop_off_diag = self.__get_piece_diag_off_diag(bishop_pos) 
            
            #The bishop may only pin if it is on the same diagonal or off diagonal as king
            if bishop_diag == king_diagonal:
                #We are on same diagonal scan for pin
                pin = self.__pin_scan(2,kingpos,bishop_pos,bishop_diag)
                #Add to pins if we have found a pint
                if pin[0] != None: pin_list.append(pin)

            elif bishop_off_diag == king_off_diagonal:
                pin = self.__pin_scan(3,kingpos,bishop_pos,bishop_off_diag)
                if pin[0] != None: pin_list.append(pin)
        
        return pin_list


    def get_pins(self)->list[tuple[int,int,int]]:
        """Returns a list of pins in the following format \n
        (pinned piece, pinned line type (0 for rank 1 for file, 2 for diagonals, 3 for off diagonals) , (line position) \n
        If not in legal mode returns empty list \n
        """
        if not self.__legal_mode:
            return []

        board = self.board
        cache = self.cache
        attacker_color = PieceColor.reverse_color(board.turn)

        #Pieces that pin king must be on the same diagonal or off diagonal
        king_pos = self.get_king_pos(self.board.turn)

        king_rank, king_file = self.__get_piece_rank_file(king_pos)
        king_diag, king_off_diag = self.__get_piece_diag_off_diag(king_pos)

        attack_rooks = board.get_locations_piece(attacker_color,PieceType.ROOK)
        attack_bishops = board.get_locations_piece(attacker_color,PieceType.BISHOP)
        attack_queens = board.get_locations_piece(attacker_color,PieceType.QUEEN)


        pins = []

        #Calculate pins for rooks and bishops, add queens to both because queens have the same 
        #Attacks of queen are just union of bishop and rook attacks so we can take care of both at same time
        pins += self.__get_pins_rook(king_pos,attack_rooks + attack_queens,king_rank,king_file)

        pins += self.__get_pins_bishop(king_pos,attack_bishops + attack_queens,king_diag,king_off_diag)

        return pins

    def __get_pieces_board(self,board:Bitboard,piece_type:int):
        
        pieces = []

        #Scans until all pieces on board have been discovered
        while 1:
            if board.value == 0:
                break
            piece = Bitboard.bitscan_reverse(board)
            pieces.append((piece,piece_type))
            board.unset(piece)

        return pieces

    def __non_slider_attacking(self,attacks:Bitboard,attacker_board:Bitboard,piece_type:int,get_attackers:bool = False)->Any:
        result = Bitboard(attacks.value & attacker_board.value)
        if not get_attackers: return result.value != 0
        #Get pieces if requested
        return self.__get_pieces_board(result,piece_type) 

    def __knight_attacking_square(self,color:int,pos:int,get_attackers:bool = False)->Any:
        """Checks if knight is attacking a given position"""
        n_attack_board = self.board.get_board_piece(color,PieceType.KNIGHT)
        #If any knight is on a square that is attacking our square return true
        return self.__non_slider_attacking(self.cache.bitm_moves_n[pos],n_attack_board,PieceType.KNIGHT,get_attackers)

    def __king_attacking_square(self,color:int,pos:int,get_attackers:bool = False)->Any:
        """Checks if king is attacking a given position"""
        k_attack_board = self.board.get_board_piece(color,PieceType.KING)
        return self.__non_slider_attacking(self.cache.bitm_moves_k[pos],k_attack_board,PieceType.KING,get_attackers)

    def __pawn_attacking_square(self,color:int,pos:int,get_attackers:bool = False)->Any:
        """Checks if a pawn is attacking a given position"""
        p_attack_board = self.board.get_board_piece(color,PieceType.PAWN)
        p_attacks = self.cache.bitm_moves_p_a_w[pos] if color == PieceColor.BLACK else self.cache.bitm_moves_p_a_b[pos]
        return self.__non_slider_attacking(p_attacks,p_attack_board,PieceType.PAWN,get_attackers)


    def __slider_attacking_square(self,color:int,pos:int,get_attackers:bool = False,remove:int = None)->Any:
        """Returns true if a slider is attacking the square in a given direction"""
        
        cache = self.cache
        squares = Bitboard(self.board.squares.value)

        if remove != None: squares.unset(remove)

        """
        Why bitscan forward / reverse?
        We want hit that is closest to the piece at a position.
        If we are going in direction of increasing indicies bitscan reverse gives that information to us
        if we are going in direction of decreasing indicies bitscan forward gives us that information
        """
        a_rook_board = self.board.get_board_piece(color,PieceType.ROOK)
        a_bishop_board = self.board.get_board_piece(color,PieceType.BISHOP)
        a_queen_board = self.board.get_board_piece(color,PieceType.QUEEN)

        attackers = []

        #Check the hits
        #If our row/collumn scan hits a rook or queen our square is being attacked 
        #if our diagonal / antidiagonal scan hits a bisop or queen our square is bieng attacked
        def check_rook(hit):
            if hit == None:return False

            if a_rook_board.occupied(hit):
                #Record attackers if requested
                if get_attackers:
                    attackers.append((hit,PieceType.ROOK))
                    #Return false here so we may continue search
                    return False
                return True
            if a_queen_board.occupied(hit):
                if get_attackers:
                    attackers.append((hit,PieceType.QUEEN))
                    return False
                return True
            return False

        def check_bishop(hit):
            if hit == None:return False
            if a_bishop_board.occupied(hit): 
                if get_attackers:
                    attackers.append((hit,PieceType.BISHOP))
                    return False
                return True
            if a_queen_board.occupied(hit):
                if get_attackers:
                    attackers.append((hit,PieceType.QUEEN))
                    return False
                return True
            return False
        
        #Bitscan in the 4 row / collumn direction
        if check_rook(self.__mask_scan(squares,cache.bitm_moves_slide_n[pos],False)): return True
        if check_rook(self.__mask_scan(squares,cache.bitm_moves_slide_w[pos],False)): return True
        if check_rook(self.__mask_scan(squares,cache.bitm_moves_slide_s[pos],True)): return True
        if check_rook(self.__mask_scan(squares,cache.bitm_moves_slide_e[pos],True)): return True


        #Bitscan in the 4 diagonal directions
        if check_bishop(self.__mask_scan(squares,cache.bitm_moves_slide_ne[pos],False)): return True
        if check_bishop(self.__mask_scan(squares,cache.bitm_moves_slide_nw[pos],False)): return True
        if check_bishop(self.__mask_scan(squares,cache.bitm_moves_slide_sw[pos],True)): return True
        if check_bishop(self.__mask_scan(squares,cache.bitm_moves_slide_se[pos],True)): return True

        if get_attackers: return attackers

        return False

    def square_attacked(self,color:int,pos:int,get_attackers = False,remove_king:bool = False):
        """
        Checks if square is attacked by pieces of a given color
        must be in legal mode to call, with remove_king set to true
        """
        if remove_king and not self.__legal_mode:
            raise self.__legal_exception("Cannon call square attacked with legal mode turned off if remove king is set to true")

        remove = self.get_king_pos(self.board.turn) if remove_king else None
        
        #Check if the given pieces are attacking square
        if not get_attackers:
            #If we are not getting attackers we can simply return after one hit
            if self.__knight_attacking_square(color,pos,False): 
                return True
            if self.__pawn_attacking_square(color,pos,False): 
                return True
            if self.__king_attacking_square(color,pos,False): 
                return True
            if self.__slider_attacking_square(color,pos,False,remove): 
                return True
            return False
        
        #Get attackers if requested, add attackers to list
        attackers = []
        attackers +=  self.__knight_attacking_square(color,pos,True)
        attackers += self.__pawn_attacking_square(color,pos,True)
        attackers += self.__king_attacking_square(color,pos,True)
        attackers += self.__slider_attacking_square(color,pos,True,remove)

        return attackers

    def __get_checkers(self,color)->list[tuple,tuple]:
        if not self.legal_mode:
            raise self.__legal_exception("Cannot get checkers if not in legal mode")
            
        king_pos = self.get_king_pos(color)
        return self.square_attacked(PieceColor.reverse_color(color),king_pos,True)

    def __posible_check(self,move:Move)->None:
        if not self.legal_mode:
            raise self.__legal_exception("Cannot evaluate possible check if legal mode is turned off")

        king_pos = self.get_king_pos(self.board.turn)

        if move.move_type == MoveType.CASTLELEFT or move.move_type == MoveType.CASTLERIGHT:
            return True

        move_rank_to, move_file_to = self.__get_piece_rank_file(move.pos_to)
        move_diag_to, move_offdiag_to = self.__get_piece_diag_off_diag(move.pos_to)

        move_rank_from, move_file_from = self.__get_piece_rank_file(move.pos_from)
        move_diag_from, move_offdiag_from = self.__get_piece_diag_off_diag(move.pos_from)


        king_rank, king_file = self.__get_piece_rank_file(king_pos)
        king_diag, king_offdiag = self.__get_piece_diag_off_diag(king_pos)

        #If we are moving from a rank that is the same as the opponents king
        #Checks are possible
        if move_rank_from == king_rank:
            return True
        if move_file_from == king_file:
            return True
        if move_diag_from == king_diag:
            return True
        if move_offdiag_from == king_offdiag:
            return True

        #Special case knight, knight attacks can attack in a box
        if move.piece == PieceType.KNIGHT or move.move_type == MoveType.PROMOTIONKNIGHT:
            if move_rank_to + 2 >= king_rank and move_rank_to- 2 <= king_rank:
                if move_file_to + 2 >= king_file and move_file_to - 2 <= king_file:
                    return True
            return False
        
        #Otherwise we must be moving to same rank/file/diagonal/antidiagonal to attack king
        if move_rank_to == king_rank:
            return True
        if move_file_to == king_file:
            return True
        if move_diag_to == king_diag:
            return True
        if move_offdiag_to == king_offdiag:
            return True


        if move.move_type != MoveType.ENPASSANT: return False

        #Special case enpassant - enpassant captures piece we are not moving to can create check
        capture_rank, capture_file = self.__get_piece_rank_file(move.caputre_pos)
        capture_diag, capture_offdiag = self.__get_piece_diag_off_diag(move.caputre_pos)

        if capture_rank == king_rank:
            return True
        if capture_file == king_file:
            return True
        if capture_diag == king_diag:
            return True
        if capture_offdiag == king_offdiag:
            return True

        
        return False

    def __update_checkers(self,move:Move = None)->None:
        """Updates check and checkers"""

        if move == None or (not move.null and self.__posible_check(move)):
            checkers = self.__get_checkers(self.board.turn)
        else:
            checkers = []
        
        self.checkers_record.append(checkers)

    def __possible_block(self,move:Move,checker_pos:int,king_pos:int)->bool:
        """Returns true if the move is moving on the same rank, file, diagonal or off diagonal as the checker"""

        move_rank, move_file = self.__get_piece_rank_file(move.pos_to)
        move_diag, move_offdiag = self.__get_piece_diag_off_diag(move.pos_to)

        checker_rank, checker_file = self.__get_piece_rank_file(checker_pos)
        checker_diag, checker_offdiag = self.__get_piece_diag_off_diag(checker_pos)

        king_rank, king_file = self.__get_piece_rank_file(king_pos)
        king_diag, king_offdiag = self.__get_piece_diag_off_diag(king_pos)

        if move_rank == checker_rank and move_rank == king_rank:
            return True
        if move_file == checker_file and move_file == king_file:
            return True
        if move_diag == checker_diag and move_diag == king_diag:
            return True
        if move_offdiag == checker_offdiag and move_offdiag == king_offdiag:
            return True


    def __in_check_move_legal(self,move:Move,pinned_pos:list[int],pins:list[tuple[int,int,int]])->bool:
        """Special move test function for when we are in check"""
        #Permited moves in check
        #    (a) - move out of check
        #    (b) - block check 
        #    (c) - capture piece
        #If there is more than one checker we must move out of check
        if not self.__legal_mode:
            raise self.__legal_exception("Cannot evaluate if move in check is legal if legal mode is not enabled")

        attacker_color = PieceColor.reverse_color(self.turn)

        #One may not castle out of check
        if move.move_type == MoveType.CASTLELEFT or move.move_type == MoveType.CASTLERIGHT:
            return False

        #Posibilities eliminated: castling out of check

        #Moving king is always a posibiliy
        if move.piece == PieceType.KING:
            square_attacked =  self.square_attacked(attacker_color,move.pos_to,get_attackers=False,remove_king=True)
            return not square_attacked


        #Firstly eliminate posibility that are straight up imposible

        #If we are in double check we must move king
        checkers = self.checkers
        if len(checkers) > 1: return False

        
        #Moving a piece that is pinned will not help us here unless it just enpassant pin
        if move.pos_from in pinned_pos:
            ind = pinned_pos.index(move.pos_from)
            pin_info = pins[ind]

            if pin_info[3] == PinType.NORMAL: return False
            #Enpassant pin case
            if move.move_type == MoveType.ENPASSANT: return False
        


        checker_pos,checker_piece = checkers[0]

        #Capturing checker is posibility
        if move.capture and move.caputre_pos == checker_pos: return True

        
        # if piece is not sliding and we are not capturing piece move is invalid
        if checker_piece == PieceType.PAWN or checker_piece == PieceType.KNIGHT: False

        king_pos = self.get_king_pos(self.board.turn)
        
        #We have elimated all other posibilities only possibility left is to block
        possible_block = self.__possible_block(move,checker_pos,king_pos)

        #Blocking not possible
        if not possible_block: return False

        #Ensure we are moving between the sliding piece and king

        if move.pos_to < king_pos and move.pos_to > checker_pos: return True
        if move.pos_to > king_pos and move.pos_to < checker_pos: return True
        
        #We have moved to right, rank / file / diagonal to block but we are not blocking
        return False


    
    def move_legal(self,move:Move,pinned_pos:list[int],pins:list[tuple[int,int,int]])->bool:
        """
        Move legality test, assumes move is pseudo legal
        Null move always returns false, however it may still be passed even if legal mode is on
        as long as king is in check
        """
        #Null move is always illegal
        if move.null: return False

        if not self.__legal_mode:
            raise self.__legal_exception("Cannot evaluate move legality if not in legal mode")



        cache = self.cache
        turn = self.board.turn
        attacker_color = PieceColor.reverse_color(turn)

        if self.in_check: return self.__in_check_move_legal(move,pinned_pos,pins)

        if move.pos_from in pinned_pos:
            #Piece is pinned, we may not move it off of it's pinned direction
            ind = pinned_pos.index(move.pos_from)
            pin_info = pins[ind]

            if pin_info[3] == PinType.NORMAL:
                #Cache stores a list of ranks, files, diagonals... look up what rank / file/.. we are trying to move to an ensure
                #That it is the same one we are pinned to
                new_line = cache.map_line_labels[pin_info[1]][move.pos_to]
                #If we are moving off of pinned line go to next move
                if new_line != pin_info[2]: return False
            else:
                #Special case enpassant pin
                if move.move_type == MoveType.ENPASSANT: return False

        #One may not move his / her / their king into check
        if move.piece == PieceType.KING:
            if self.square_attacked(attacker_color,move.pos_to,remove_king=True): return False
        #One may not castle through check
        if move.move_type == MoveType.CASTLELEFT:
            if self.square_attacked(attacker_color,move.pos_from - 1): return False
            if self.square_attacked(attacker_color,move.pos_from - 2): return False
        if move.move_type == MoveType.CASTLERIGHT:
            if self.square_attacked(attacker_color,move.pos_from + 1): return False
            if self.square_attacked(attacker_color,move.pos_from + 2): return False

        return True

    def get_moves_pseudo_legal(self)->list[Move]:
        if self.is_draw() : return []
        return PseudoMoveGenerator.get_pseudo_all(self.board,self.cache)

    def get_moves_pseudo_legal_piece(self,piece_type:int)->list[Move]:
        if self.is_draw() : return []
        return PseudoMoveGenerator.get_pseudo_piece(self.board,self.cache,piece_type)

    def get_moves_pseudo_legal_pos(self,pos:int)->list[Move]:
        if self.is_draw() : return []
        return PseudoMoveGenerator.get_pseudo_pos(self.board,self.cache,pos)

    def __get_legal(self,pseudo_moves:list[Move])->list[Move]:
        """Checks a list of pseudo legal moves and returns legality of the moves"""
        pins = self.get_pins()
        pinned_pos = [pin[0] for pin in pins]

        return [move for move in pseudo_moves if self.move_legal(move,pinned_pos,pins)]

    def get_moves(self)->list[Move]:
        """Returns a list of legal moves from the position"""
        if not self.legal_mode:
            raise self.__legal_exception("Cannot get legal moves if legal mode is not enabled")

        pseudo_moves = self.get_moves_pseudo_legal()
        return self.__get_legal(pseudo_moves)

    def get_moves_pos(self,pos:int)->list[Move]:
        """Returns all moves for the piece at given postion: TODO: make it so not all moves are calculated just to get one piece's moves"""
        if not self.legal_mode:
            raise self.__legal_exception("Cannot get legal moves if legal mode is not enabled")

        pseudo_moves = self.get_moves_pseudo_legal_pos(pos)

        return self.__get_legal(pseudo_moves)


    def move(self,move:Move):
        """Makes move. Does not check if move is legal."""
        #Special processing required for null move
        #1 - ensure null move is allowed
        #2 - Ensure we are not in check if legal mode is on

        if move.null:
            if not self.allow_null and move.null:
                raise self.__legal_exception("Null move was passed when null moves are disabled")
            if self.legal_mode and self.in_check:
                raise self.__legal_exception("Null move cannot be passed when in check if legal mode is on")


        #Execute move and add move to move stack and instruction to instruction stack
        inst = MoveProcessor.execute_move(self.board,self.cache,move)
        self.instruction_stack.append(inst)
        self.move_stack.append(move)

        #Add hash of board to our hashed positions 
        self.__update_hash(inst)

        #Ensure we are not capturing king if we are in legal mode
        if self.__legal_mode:
            #No need to update checkers for null move
            self.__update_checkers(move)
            if move.capture and move.capure_piece == PieceType.KING:
                raise self.__legal_exception("Cannot capture king in legal mode!")
    
    def __update_hash(self,instruction:MoveInstruction)->None:
        """
        Incremental update to hash
        using fact that XOR is it's own inverse
        https://www.chessprogramming.org/Zobrist_Hashing
        """
        hash = ChessHashing.update_instruction(self.reached_positions[-1],self.cache,instruction)
        self.reached_positions.append(hash)


        

    def unmove(self):
        """Undoes last move in stack."""
        self.board.undo(self.instruction_stack[-1])
        del self.checkers_record[-1]
        del self.instruction_stack[-1]
        del self.move_stack[-1]
        del self.reached_positions[-1]


    def set_fen(self,fen:str):
        """Sets board to specified FEN, resets history"""
        board = BoardIO.from_fen(fen)
        self.set_board(board)

    def set_board(self,board:Board):
        self.board = board
        self.instruction_stack = []
        self.checkers_record = []
        self.reached_positions = [ChessHashing.hash(self.cache,board)]
        self.__update_checkers()


    def loop_moves(self,evaluate:Callable[[Move],bool] = None,presort_key:Callable[[Move],int] = None,include_key:Callable[[Move],bool] = None) -> None:
        """
        Loops through selected moves in an order determined by presort_key, makes move and undoes it. \n
        Calls evaluate(Move) before undoing \n
        presort_key - uses this function to sort moves, sorts from greatest to smallest \n
        include_key - uses this function to exclude / include moves in the loop
        """
        if not self.legal_mode:
            raise self.__legal_exception("Cannot get legal moves if legal mode is not enabled")

        pseudo_moves = self.get_moves_pseudo_legal()

        excluded_moves = [move for move in pseudo_moves if include_key(move)] if include_key != None else pseudo_moves

        legal_moves = self.__get_legal(excluded_moves)
        
        sorted_moves = sorted(legal_moves,key=presort_key,reverse=True) if presort_key != None else legal_moves        

        for move in sorted_moves:
            self.move(move)
            cont = evaluate(move) if evaluate != None else True
            self.unmove()

            if not cont: break




    def perft(self,depth)->int:
        #Turn off three fold repitions for perft evaluation
        threefold = self.can_draw
        self.can_draw = False

        if not self.legal_mode:
            raise self.__legal_exception("Cannot run perft if legal mode is note enabled")
        
        depth_left = depth
        count = 0
        
        def loop(move:Move)->bool:
            nonlocal depth_left,count

            if depth_left - 1 == 0:
                count += 1

                return True
            
            depth_left -= 1

            self.loop_moves(loop)

            depth_left += 1

            return True

        self.loop_moves(loop)

        self.can_draw = threefold
        return count

    def has_legal_moves(self):
        """Returns true if the player whose turn it is has legal moves"""
        if not self.legal_mode:
            raise self.__legal_exception("Cannot get legal moves if legal mode is not enabled")

        pins = self.get_pins()
        pinned_pos = [pin[0] for pin in pins]
        pseudo_moves = self.get_moves_pseudo_legal()

        for move in pseudo_moves:
            if self.move_legal(move,pinned_pos,pins):
                return True

        return False

    def in_checkmate(self)->bool:
        """Returns true if the board in checkmate state"""
        if not self.legal_mode:
            raise self.__legal_exception("Cannot evaluate checkmate if legal mode is not enabled")

        if not self.in_check:
            #If we are not in check we cannot be in checkmate
            return False
        if self.is_draw():
            #It is possible to be in check and have no moves but not be in checkmate if game is drawn
            return False

        return not self.has_legal_moves()

    def is_draw(self)->bool:
        """Returns true if 50 move rule has been reached or we have threefold repitition or material is insuficient"""
        if not self.can_draw: return False
        #Check 50 move rule
        if self.board.half_move >= 50:
            return True
        if operator.countOf(self.reached_positions,self.current_hash) >= 3:
            return True
        if not self.__has_suficient_material():
            return True

        
        #To do implement sufficient material check
        return False

    def __has_suficient_material(self)->bool:
        """Checks if there is enought material to not be draw"""
        #Check sufficient material
        board = self.board
        """
        Insuficient material conditions
        https://support.chess.com/article/128-what-does-insufficient-mating-material-mean

        We can draw if king is lone
        if both sides have one of the following
        -lone king
        -king + bishop
        -king and knight
        -king and two knights
        """

        #If any pawns are on board we can continue
        if board.get_board_piece(PieceColor.BLACK,PieceType.PAWN).value != 0:
            return True
        if board.get_board_piece(PieceColor.WHITE,PieceType.PAWN).value != 0:
            return True
        #If a queen or rook are on we can continue
        if board.get_board_piece(PieceColor.BLACK,PieceType.ROOK).value != 0:
            return True
        if board.get_board_piece(PieceColor.WHITE,PieceType.ROOK).value != 0:
            return True
        if board.get_board_piece(PieceColor.BLACK,PieceType.QUEEN).value != 0:
            return True
        if board.get_board_piece(PieceColor.WHITE,PieceType.QUEEN).value != 0:
            return True

        #CASE: All pieces are gone except knights, bishops and king

        n_count_w = board.get_piece_count(PieceColor.WHITE,PieceType.KNIGHT)
        n_count_b = board.get_piece_count(PieceColor.BLACK,PieceType.KNIGHT)
        b_count_w = board.get_piece_count(PieceColor.WHITE,PieceType.BISHOP)
        b_count_b = board.get_piece_count(PieceColor.BLACK,PieceType.BISHOP)

        #Check if we have enougt knigts / bishops to coninue
        suf_white = self.__suf_knight_bishop(n_count_w,b_count_w,n_count_b,b_count_b)
        suf_black = self.__suf_knight_bishop(n_count_b,b_count_b,n_count_w,b_count_w)

        #If either side has sufficient material it is not a draw
        return suf_white or suf_black


        
    def __suf_knight_bishop(self,n_count,b_count,n_count_other,b_count_other):

        suf = True
        if b_count == 0:
            #No bishops only knights
            #1 knight is a draw
            if n_count <= 1:
                suf = False
            #Two knights and the other side have no other pieces is a draw
            if n_count == 2 and n_count_other + b_count_other == 0:
                suf = False
        elif n_count == 0:
            #No knights only bishops 
            #Need more than one bishop
            if b_count <= 1:
                suf = False  

        return suf

            
    @property
    def terminal_status(self)->int:
        """Checks state of game and sees if it can continue \n
        Returns terminal status, either not terminal (0), checkmate (1), stalemate (2)"""
        if self.has_legal_moves(): return TerminalStatus.NotTerminal

        if self.in_checkmate(): return TerminalStatus.Checkmate

        if self.is_draw(): return TerminalStatus.Draw
        
        return TerminalStatus.Stalemate


    def __init__(self,board:Board,cache:MoveCache,legal_mode:bool = True) -> None:
        self.board = board
        self.cache = cache
        self.instruction_stack = []
        self.checkers_record = []
        self.move_stack = []
        self.reached_positions = [ChessHashing.hash(self.cache,self.board)]

        self.legal_mode = legal_mode

        if legal_mode:
            self.__update_checkers()

def pin_test():
    board = BoardIO.from_fen(FEN.ATTACK_TEST_1)
    cache = MoveCache()

    me = MoveEngine(board,cache)

    attacked = me.square_attacked(PieceColor.WHITE,0)
    print(attacked)

def test():
    board = BoardIO.from_fen(FEN.KING_MOVE_TEST)
    cache = MoveCache()

    me = MoveEngine(board,cache)
    lms = me.get_moves()
    
    pass

def perft_test_movegen():
    board = BoardIO.from_fen(FEN.START_POS)
    cache = MoveCache()

    me = MoveEngine(board,cache)

    show_perf = False
    if show_perf:
        pr = cProfile.Profile()
        pr.enable()

    BoardIO.print_board(me.board)

    t1 = time.perf_counter()
    moves = me.get_moves()

    perft_result = me.perft(5)

    t2 = time.perf_counter()

    if show_perf:
        pr.disable()
        s = io.StringIO()
        sortby = SortKey.CUMULATIVE
        ps = pstats.Stats(pr,stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())

    print(f"{perft_result} nodes in {(t2-t1):.2f} (s)")

    input()
    

def debug():
    board = BoardIO.from_fen(FEN.START_POS)
    cache = MoveCache()

    me = MoveEngine(board,cache)

    show_perf = False
    if show_perf:
        pr = cProfile.Profile()
        pr.enable()

    #pos_from = Bitboard.get_pos(1,4)
    #moves = me.get_moves_piece(pos_from)
    #for move in moves:
    #    if move.pos_to == Bitboard.get_pos(0,4):
    #        me.move(move)
#
    #pos_from = Bitboard.get_pos(7,3)
    #moves = me.get_moves_piece(pos_from)
    #for move in moves:
    #    if move.pos_to == Bitboard.get_pos(6,3):
    #        me.move(move)
#
    pos_from = Bitboard.get_pos(0,6)
    moves = me.get_moves_piece(pos_from)
    me.move(moves[0])

    pos_from = Bitboard.get_pos(5,1)
    moves = me.get_moves_piece(pos_from)
    me.move(moves[1])

    pos_from = Bitboard.get_pos(6,7)
    moves = me.get_moves_piece(pos_from)
    for move in moves:
        if move.pos_to == Bitboard.get_pos(5,5):
            me.move(move)



    BoardIO.print_board(me.board)

    t1 = time.perf_counter()

    t2 = time.perf_counter()

    if show_perf:
        pr.disable()
        s = io.StringIO()
        sortby = SortKey.CUMULATIVE
        ps = pstats.Stats(pr,stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())

    #print(f"{perft_result} nodes in {(t2-t1):.2f} (s)")

    input()

if __name__ == "__main__":
    perft_test_movegen()