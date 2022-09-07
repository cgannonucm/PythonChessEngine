from board import *
from movecache import *
from pseudomoves import Move,MoveProcessor

class ChessHashing:
    """Class provides methods for hashing chess board"""

    @staticmethod
    def hash_piece(hash:int,cache:MoveCache,piece_type:int,pos:int,color:int)->int:
        return hash ^ cache.get_hash_piece(piece_type,pos,color)

    @staticmethod
    def hash_castle(hash:int,cache:MoveCache,castle_rights:CastleRights)->int:
        return hash ^ cache.get_hash_castling_rights(castle_rights)

    @staticmethod
    def hash_enpassant_target(hash:int,cache:MoveCache, enpassant_target:int)->int:
        if enpassant_target != None:
            return hash ^ cache.get_hash_enpassant(enpassant_target)
        return hash
    

    @staticmethod
    def hash_turn(hash:int,cache:MoveCache,turn:int)->int:
        if turn == PieceColor.BLACK:
            return hash ^ cache.get_hash_turn(turn)
        return hash



    @staticmethod
    def hash(cache:MoveCache,board:Board) -> int:
        """
        Returns zobrist hash of board
        https://www.chessprogramming.org/Zobrist_Hashing
        """
        hash = BitTwiddle.zero

        #Hash all pieces
        for color in range(2):
            for piece_type in range(6):
                positions = board.get_locations_piece(color,piece_type)
                for pos in positions:
                    hash = ChessHashing.hash_piece(hash,cache,piece_type,pos,color)


        #Hash castling rights
        hash = ChessHashing.hash_castle(hash,cache,board.castle_rights)
        
        #Hash enpassant target
        hash = ChessHashing.hash_enpassant_target(hash,cache,board.enpassant_target)
        
        #Hash turn
        hash = ChessHashing.hash_turn(hash,cache,board.turn)

        return hash
    

    @staticmethod
    def update_instruction(hash:int,cache:MoveCache,instruction:MoveInstruction):
        """
        Incrementally upadate the given zobrist hash according to the given move instruction
        https://www.chessprogramming.org/Zobrist_Hashing
        """
        #using fact that XOR is it's own inverse we can hash a position without recalculating everything
        #https://www.chessprogramming.org/Zobrist_Hashing

        _hash = hash
        color = instruction.move_from_color
        
        #If move is not the null move check for moves / captures / special moves
        if not instruction.null:
        #Remove capture if the move was a capture
            if instruction.capture:
                _hash = ChessHashing.hash_piece(_hash,cache,instruction.capture_piece,instruction.capture_pos,instruction.capture_color)
            elif instruction.castle:
                #Remove rook from old position and add to new position
                _hash = ChessHashing.hash_piece(_hash,cache,PieceType.ROOK,instruction.rook_pos_from,color)
                _hash = ChessHashing.hash_piece(_hash,cache,PieceType.ROOK,instruction.rook_pos_to,color)

            #Remove piece from location we are moving from
            _hash = ChessHashing.hash_piece(_hash,cache,instruction.move_from_piece,instruction.move_from,color)

            #Add in piece at location we are moving to
            _hash = ChessHashing.hash_piece(_hash,cache,instruction.move_to_piece,instruction.move_to,color)

        #Update castling rights
        #Undo previous castling rights
        _hash = ChessHashing.hash_castle(_hash,cache,instruction.castling_rights_previous)
        #Hash new castling rights
        _hash = ChessHashing.hash_castle(_hash,cache,instruction.castling_rights_current)

        #Update enpassant target
        #Undo previous enpassant target
        _hash = ChessHashing.hash_enpassant_target(_hash,cache,instruction.enpassant_target_previous)
        #Hash new enpassant target
        _hash = ChessHashing.hash_enpassant_target(_hash,cache,instruction.enpassant_target_current)

        #Advance turn
        #To advance turn we always XOR hash by the black turn color
        #When hashing we only XOR hash by black turn hash when it is black's turn
        #nothing is done on white's turn
        #by XOR ing hash by black turn hash we undo black turn if it's whites turn and
        #go to black's turn if it is black's turn
        _hash = ChessHashing.hash_turn(_hash,cache,PieceColor.BLACK)

    
        return _hash

    

    @staticmethod
    def update(hash:int,cache:MoveCache,move:Move,board:Board):
        """
        Incrementally upadate the given zobrist hash according to the given Move
        https://www.chessprogramming.org/Zobrist_Hashing
        """
        inst = MoveProcessor.process_move(board,cache,move)
        return ChessHashing.update_instruction(hash,cache,inst)
    

