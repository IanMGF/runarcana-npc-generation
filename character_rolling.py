from random import random, choices
import json
import d20

wealth_mod_table = {
    "Miserável": 0.6,
    "Esquálido": 0.8,
    "Pobre": 0.9,
    "Modesto": 1,
    "Confortável": 1.2,
    "Rico": 1.6,
    "Aristocrático": 2
}



class CharacterBuilder:
    def __init__(self, depth, char_factors=None):
        if char_factors is None:
            char_factors = {}

        self.depth = depth
        self.char_factors = char_factors
        self.tendencies = { }

        self.roll_if_null("location", "Região", extract_result=True)
        local_tendencies = local_modifiers[self.char_factors["location"]]["tendencies"]
        for tendency in local_tendencies:
            self.tendencies[tendency] = self.tendencies.get(tendency, 1) * local_tendencies[tendency]

        self.roll_if_null("class", "Classes")
        self.roll_if_null("class_reason", self.char_factors["class"]["result"])
        self.roll_if_null("past", "Passados")
        self.roll_if_null("past_reason", self.char_factors["past"]["result"])

        self.roll_if_null("parents", "Pais")
        self.roll_if_null("birthplace", "Local de Nascimento")

        self.roll_if_null("tutors", "Responsáveis")

        self.roll_if_null("youth", "Memórias da Juventude")

        location_modifier = local_modifiers[self.char_factors["location"]]

        location_wealth_mod = lambda weights: [(location_modifier["wealth"] ** -w) * weights[w] for w in
                                               range(len(weights))]
        self.roll_if_null("lifestyle", "Estilo de Vida Familiar", w_func=location_wealth_mod)

        wealth_modifier = wealth_mod_table[self.char_factors["lifestyle"]["result"]]
        positive_wealth_weights = lambda weights: [wealth_modifier ** -(1 + 0.2 * w) * weights[w] for w in
                                                   range(len(weights))]
        negative_wealth_weights = lambda weights: [wealth_modifier ** (1 + 0.2 * w) * weights[w] for w in
                                                   range(len(weights))]

        self.roll_if_null("siblings", "Número de Irmãos", w_func=positive_wealth_weights)
        self.char_factors["siblings"] = d20.roll(self.char_factors["siblings"]["result"]).total

        self.roll_if_null("birth_order", "Ordem de Nascimento")
        self.roll_if_null("grow_location", "Lar na Infância", w_func=negative_wealth_weights)


    def roll(self, table, extra_weights=None, new_char_factors=None, w_func=None):
        return roll_on_table(tables[table],
                             deep=self.depth-1,
                             base_char=self,
                             new_char_factors=new_char_factors,
                             w_func=w_func,
                             extra_weights=extra_weights)

    def roll_if_null(self, property_name, table_name, extract_result=False, new_char_factors=None, w_func=None):
        if property_name not in self.char_factors:
            extra_weights = {}
            if property_name in self.tendencies:
                extra_weights = self.tendencies[property_name]
            rolled_factor = self.roll(table_name, extra_weights=extra_weights, new_char_factors=new_char_factors, w_func=w_func)
            if extract_result:
                rolled_factor = rolled_factor["result"]
            self.char_factors[property_name] = rolled_factor


with open("resources/NPC Generator/location_modifiers.json", encoding="utf-8") as location_modifiers_file:
    local_modifiers = json.load(location_modifiers_file)

def roll_on_table(table: list, extra_weights=None, w_func=None, deep=5, new_char_factors=None, base_char=None):
    if base_char is None and deep > 0:
        base_char = CharacterBuilder(deep)


    weights = [item["chance"] for item in table]
    if extra_weights is not None:
        table_weights = dict([(item["result"], item) for item in table])
        for extra_weight in extra_weights:
            item = table_weights[extra_weight]
            item_index = table.index(item)
            weights[item_index] *= extra_weights[extra_weight]

    if w_func is not None:
        weights = w_func(weights)

    read_item = choices(table, weights=weights, k=1)[0]
    new_item = { }
    new_item.update(read_item)
    del new_item["chance"]

    if "extra_rolls" in read_item:
        del new_item["extra_rolls"]
        extras = []
        if new_char_factors is None:
            new_char_factors = {}

        for extra in read_item["extra_rolls"]:
            if extra.startswith("Novo personagem"):

                extra_character = extra[len("Novo personagem"):]
                if extra_character == "": extra_character = "Personagem"
                if deep <= 0:
                    continue
                elif "location" in new_char_factors:
                    continue
                else:
                    base_location = base_char.char_factors["location"]
                    char_local = local_modifiers[base_location]
                    origin_weights = char_local["origin_weights"]
                    location_weights = [origin_weights[item] for item in origin_weights]
                    location_names = [item for item in origin_weights]
                    new_char_factors["location"] = choices(location_names, location_weights, k=1)[0]
                extras.append({"id": f"{extra_character}", "extra": CharacterBuilder(deep, char_factors=new_char_factors).char_factors})
            else:
                extras.append({"id": extra, "extra": roll_on_table(tables[extra], deep=deep - 1, **new_char_factors)})
        new_item["extras"] = extras

    return new_item


with open("resources/NPC Generator/life_building.json", encoding="utf-8") as life_building:
    tables = json.load(life_building)


def filter_results(dictionary: dict):
    for key in dictionary:
        value = dictionary[key]
        if isinstance(value, dict):
            if "result" in value.keys() and len(value.keys()) == 1:
                dictionary[key] = value["result"]
            else:
                filter_results(value)
        elif isinstance(value, list):
            for list_item in value:
                filter_results(list_item)


for char_index in range(50):
    data = CharacterBuilder(char_factors={
        "location": "Zaun" if random() < 0.7 else "Piltover"
    }, depth=4).char_factors
    formatted_data = data.copy()
    filter_results(formatted_data)

    with open(f"resources/NPC Generator/NPCs/NPC {char_index}.json", encoding="utf-8", mode="w") as npc_file:
        json.dump(formatted_data, npc_file, ensure_ascii=False, indent=4, sort_keys=False)
