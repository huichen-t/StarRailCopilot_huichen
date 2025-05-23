from tasks.map.control.waypoint import Waypoint
from tasks.map.keywords.plane import Amphoreus_StrifeRuinsCastrumKremnos
from tasks.ornament.route_base import RouteBase


class Route(RouteBase):

    def Amphoreus_StrifeRuinsCastrumKremnos_F1OE_X373Y317(self):
        """
        | Waypoint | Position                  | Direction | Rotation |
        | -------- | ------------------------- | --------- | -------- |
        | spawn    | Waypoint((373.2, 317.4)), | 4.2       | 1        |
        | enemy    | Waypoint((368.4, 281.3)), | 11.2      | 4        |
        """
        self.map_init(plane=Amphoreus_StrifeRuinsCastrumKremnos, floor="F1OE", position=(373.2, 317.4))
        enemy = Waypoint((368.4, 281.3))
        # ===== End of generated waypoints =====

        self.minimap.lock_rotation(0)
        self.clear_enemy(enemy)
