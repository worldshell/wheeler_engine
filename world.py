import yaml
from typing import Dict, List, Optional, Any

class GameObject:
    def __init__(self, data: Dict[str, Any], type_def: Dict[str, Any]):
        self.id = data['id']
        self.type = data['type']
        # 如果有name字段就用，否则从id生成
        self.name = data.get('name', data['id'].replace('_', ' ').title())
        self.location = data['location']
        # Merge type properties with instance state
        self.properties = type_def.get('properties', {}).copy()
        self.state = data.get('state', {}).copy()
        
        # Door specific: link between rooms
        self.link = data.get('link', [])
        
        # Specific properties handling
        self.is_container = self.properties.get('can_contain_items', False)
        self.is_lockable = self.properties.get('can_lock', False)
        self.is_portable = self.properties.get('portable', False)
        self.is_opaque = self.properties.get('is_opaque', False)

    def describe(self) -> str:
        status = []
        if self.is_container:
            if self.state.get('is_open'):
                status.append("已打开")
            else:
                status.append("关闭")
        if self.is_lockable:
            if self.state.get('is_locked'):
                status.append("上锁")
            else:
                status.append("未锁")
        
        desc = f"{self.name}"
        if status:
            desc += f" ({', '.join(status)})"
        return desc

class Room:
    def __init__(self, id: str, data: Dict[str, Any]):
        self.id = id
        self.name = data['name']
        self.description = data['description']
        self.connections = data.get('connections', {})
        self.objects: List[GameObject] = []
        # Dynamic traces left in this room
        self.traces: List[Dict[str, Any]] = [] 

    def add_object(self, obj: GameObject):
        self.objects.append(obj)

    def remove_object(self, obj: GameObject):
        if obj in self.objects:
            self.objects.remove(obj)

    def get_object(self, obj_id: str) -> Optional[GameObject]:
        for obj in self.objects:
            if obj.id == obj_id:
                return obj
        return None

class World:
    def __init__(self, yaml_path: str):
        with open(yaml_path, 'r', encoding='utf-8') as f:
            self.data = yaml.safe_load(f)
        
        self.rooms: Dict[str, Room] = {}
        self.objects: Dict[str, GameObject] = {}
        self.object_types: Dict[str, Dict] = {t['name']: t for t in self.data['object_types']}
        self.trace_rules = self.data.get('trace_rules', [])

        self._build_world()

    def _build_world(self):
        # 1. Build Rooms
        for room_id, room_data in self.data['rooms'].items():
            self.rooms[room_id] = Room(room_id, room_data)

        # 2. Build Objects
        for obj_data in self.data['entities']:
            obj_type_def = self.object_types.get(obj_data['type'], {})
            # Handle inheritance roughly
            if 'inherits' in obj_type_def:
                parent_type = self.object_types.get(obj_type_def['inherits'], {})
                # Merge parent properties (child overrides parent)
                parent_props = parent_type.get('properties', {}).copy()
                parent_props.update(obj_type_def.get('properties', {}))
                obj_type_def['properties'] = parent_props

            obj = GameObject(obj_data, obj_type_def)
            self.objects[obj.id] = obj
            
            # Place in room or inside another container?
            # For simplicity in this demo, 'location' refers to room ID or container ID
            # We'll put everything in a flat registry first, then resolve containment if needed.
            # Here we assume location is a Room ID for simplicity of the MVP.
            if obj.location in self.rooms:
                self.rooms[obj.location].add_object(obj)
            # If location is another object (container), we handle it separately logic-wise
            # or we iterate again. For MVP, let's assume flat room placement or handle container placement.
            
        # 2.1 Handle containment (Objects inside objects)
        # We need a second pass or check if location is not a room
        for obj in self.objects.values():
            if obj.location not in self.rooms and obj.location in self.objects:
                parent_obj = self.objects[obj.location]
                if 'contains' not in parent_obj.state:
                    parent_obj.state['contains'] = []
                parent_obj.state['contains'].append(obj.id)
                # It's physically in the container, so logically it's in the room of the container?
                # Or we just track it abstractly.
                # Let's keep it abstract. If you search the container, you find it.

    def get_room(self, room_id: str) -> Optional[Room]:
        return self.rooms.get(room_id)

    def get_object(self, obj_id: str) -> Optional[GameObject]:
        return self.objects.get(obj_id)
