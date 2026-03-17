class Player:
    def __init__(self, name: str, rating: int, fide_id: str = None, federation: str = "UNK"):
        self.name = name
        self.rating = rating
        self.fide_id = fide_id
        self.federation = federation
