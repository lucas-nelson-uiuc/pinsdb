from typing import Sequence
from attrs import define, field


@define
class Bowler:
    bowler_id: str
    nicknames: Sequence[str] = field(factory=tuple)


Alek = Bowler(bowler_id="Alek", nicknames=("A", "AL", "ALE", "ALK", "ALEK", "POP"))
Cam = Bowler(bowler_id="Cam", nicknames=("C", "CA", "CAM", "CAMERON"))
Drew = Bowler(bowler_id="Drew", nicknames=("D", "DRE", "DRW", "DREW"))
Jake = Bowler(bowler_id="Jake", nicknames=("J", "JAK", "JAKE"))
Lucas = Bowler(bowler_id="Lucas", nicknames=("L", "LUC", "LOU", "LUN", "LUCAS"))
Naomi = Bowler(bowler_id="Naomi", nicknames=("N", "NAOMI"))
Ryley = Bowler(bowler_id="Ryley", nicknames=("R", "RY", "RYL", "RYLEY"))
Sara = Bowler(bowler_id="Sara", nicknames=("SARA"))
Spencer = Bowler(bowler_id="Spencer", nicknames=("S", "SPE", "SPO", "SPEN", "SPENCER"))

registered_bowlers = (
    Alek,
    Cam,
    Drew,
    Jake,
    Lucas,
    Naomi,
    Ryley,
    Sara,
    Spencer,
)
