#!/usr/bin/env python3
"""
Add rich context data to aircraft_list.json for enhanced email alerts
"""
import json

# Celebrity aircraft context data
CELEBRITY_CONTEXT = {
    "Taylor Swift": {
        "N621MM": {
            "net_worth": "$1.1 billion (2024)",
            "aircraft_value": "$54 million",
            "specs": {
                "range": "5,950 nautical miles",
                "speed": "Mach 0.90 (690 mph)",
                "passengers": "Up to 16"
            },
            "fun_facts": [
                "Most tracked celebrity jet in the world - sparked climate activism debates",
                "Used extensively during record-breaking Eras Tour - traveled 125,000+ miles in 2023",
                "Can fly nonstop from Los Angeles to London or New York to Tokyo",
                "Features luxury cabin with full galley, bedroom suite, and entertainment systems"
            ],
            "wikipedia": "https://en.wikipedia.org/wiki/Taylor_Swift"
        }
    },
    "Drake": {
        "N767CJ": {
            "net_worth": "$250 million (2024)",
            "aircraft_value": "$220 million (customized)",
            "specs": {
                "range": "6,385 nautical miles",
                "speed": "Mach 0.80 (528 mph)",
                "passengers": "30+ capacity"
            },
            "fun_facts": [
                "Nicknamed 'Air Drake' - one of the most extravagant celebrity jets",
                "Custom interior with master bedroom, private casino, full bar, and gold fixtures",
                "Originally a commercial airliner, converted into ultra-luxury private jet",
                "Gift from Cargojet Airways in 2019 - features massive OVO owl logo on tail"
            ],
            "wikipedia": "https://en.wikipedia.org/wiki/Drake_(musician)"
        }
    },
    "Jeff Bezos": {
        "N11AF": {
            "net_worth": "$196 billion (2024)",
            "aircraft_value": "$80 million",
            "specs": {
                "range": "7,500 nautical miles",
                "speed": "Mach 0.925 (710 mph)",
                "passengers": "Up to 19"
            },
            "fun_facts": [
                "Brand new Gulfstream G700 delivered July 2024 - latest flagship model",
                "Most advanced business jet in the world with cutting-edge avionics",
                "Can fly non-stop from New York to Singapore or LA to Sydney",
                "Features panoramic windows, ultra-quiet cabin, and circadian lighting system"
            ],
            "wikipedia": "https://en.wikipedia.org/wiki/Jeff_Bezos"
        },
        "N758PB": {
            "net_worth": "$196 billion (2024)",
            "aircraft_value": "$70 million",
            "specs": {
                "range": "7,000 nautical miles",
                "speed": "Mach 0.925 (710 mph)",
                "passengers": "Up to 18"
            },
            "fun_facts": [
                "Secondary G650 for simultaneous trips or backup operations",
                "Managed through Poplar Glen LLC for privacy",
                "Can fly at 51,000 feet - higher than almost all other jets",
                "One of the fastest civilian aircraft in the world"
            ],
            "wikipedia": "https://en.wikipedia.org/wiki/Jeff_Bezos"
        }
    },
    "Elon Musk": {
        "N628TS": {
            "net_worth": "$195 billion (2024)",
            "aircraft_value": "$70 million",
            "specs": {
                "range": "7,500 nautical miles",
                "speed": "Mach 0.925 (710 mph)",
                "passengers": "Up to 18"
            },
            "fun_facts": [
                "Most tracked private jet in history - inspired @ElonJet Twitter account controversy",
                "Flies between Tesla factories, SpaceX sites, and Twitter/X HQ constantly",
                "Used for rapid international trips - can reach Europe or Asia from US non-stop",
                "Registered to Falcon Landing LLC (named after SpaceX's rocket landing program)"
            ],
            "wikipedia": "https://en.wikipedia.org/wiki/Elon_Musk"
        },
        "N272BG": {
            "net_worth": "$195 billion (2024)",
            "aircraft_value": "$45 million",
            "specs": {
                "range": "6,750 nautical miles",
                "speed": "Mach 0.87 (668 mph)",
                "passengers": "Up to 16"
            },
            "fun_facts": [
                "Older G550 used for employee transport and shorter regional trips",
                "Often shuttles SpaceX engineers between facilities",
                "Backup aircraft when G650ER is in maintenance",
                "Also registered to Falcon Landing LLC"
            ],
            "wikipedia": "https://en.wikipedia.org/wiki/Elon_Musk"
        }
    },
    "Kim Kardashian": {
        "N1980K": {
            "net_worth": "$1.7 billion (2024)",
            "aircraft_value": "$95 million (custom interior)",
            "specs": {
                "range": "7,500 nautical miles",
                "speed": "Mach 0.925 (710 mph)",
                "passengers": "Up to 18"
            },
            "fun_facts": [
                "Nicknamed 'Kim Air' - features all-beige custom cashmere interior",
                "Interior designed by Waldo Fernandez and Tommy Clements",
                "Seats convert to lie-flat beds with custom bedding",
                "Tail number ends in '80K' - matching her birth year and estimated cost"
            ],
            "wikipedia": "https://en.wikipedia.org/wiki/Kim_Kardashian"
        }
    },
    "Mark Zuckerberg": {
        "N68885": {
            "net_worth": "$177 billion (2024)",
            "aircraft_value": "$70 million",
            "specs": {
                "range": "7,500 nautical miles",
                "speed": "Mach 0.925 (710 mph)",
                "passengers": "Up to 18"
            },
            "fun_facts": [
                "Primary jet for Meta business travel and international trips",
                "Used for philanthropic missions via Chan Zuckerberg Initiative",
                "Can reach anywhere in the world with single refueling stop",
                "Features advanced security and communications systems"
            ],
            "wikipedia": "https://en.wikipedia.org/wiki/Mark_Zuckerberg"
        },
        "N3880": {
            "net_worth": "$177 billion (2024)",
            "aircraft_value": "$80 million",
            "specs": {
                "range": "7,500 nautical miles",
                "speed": "Mach 0.925 (710 mph)",
                "passengers": "Up to 19"
            },
            "fun_facts": [
                "Brand new G700 delivered 2024 - same model as Bezos",
                "Most advanced business jet with revolutionary cabin design",
                "Features ultra-high-speed internet for remote work at 45,000 feet",
                "20 panoramic windows - largest in business aviation"
            ],
            "wikipedia": "https://en.wikipedia.org/wiki/Mark_Zuckerberg"
        }
    },
    "Donald Trump": {
        "N757AF": {
            "net_worth": "$2.6 billion (est. 2024)",
            "aircraft_value": "$100+ million (customized)",
            "specs": {
                "range": "4,200 nautical miles",
                "speed": "Mach 0.80 (530 mph)",
                "passengers": "43 capacity"
            },
            "fun_facts": [
                "Nicknamed 'Trump Force One' - famously used during presidential campaigns",
                "Interior features 24-karat gold plated fixtures and seatbelts",
                "Former commercial airliner (built 1991) converted to luxury transport",
                "Master bedroom, dining room, guest suites, and shower on board"
            ],
            "wikipedia": "https://en.wikipedia.org/wiki/Donald_Trump"
        }
    },
    "Michael Bloomberg": {
        "N5MV": {
            "net_worth": "$106 billion (2024)",
            "aircraft_value": "$55 million",
            "specs": {
                "range": "4,750 nautical miles",
                "speed": "Mach 0.87 (668 mph)",
                "passengers": "Up to 14"
            },
            "fun_facts": [
                "Primary corporate jet for Bloomberg LP business operations",
                "Used for rapid trips between financial capitals worldwide",
                "Bloomberg operates multiple jets for flexibility",
                "Features secure communications for sensitive business matters"
            ],
            "wikipedia": "https://en.wikipedia.org/wiki/Michael_Bloomberg"
        }
    }
}

def load_aircraft_list():
    """Load current aircraft list"""
    with open('/home/kurt/flighttrak/aircraft_list.json', 'r') as f:
        return json.load(f)

def save_aircraft_list(data):
    """Save updated aircraft list"""
    with open('/home/kurt/flighttrak/aircraft_list.json', 'w') as f:
        json.dump(data, f, indent=4)
    print("✓ Saved updated aircraft_list.json")

def add_context_data(data):
    """Add context data to celebrity aircraft"""
    updated = 0

    for aircraft in data['aircraft_to_detect']:
        owner = aircraft.get('owner', '')
        tail = aircraft.get('tail_number', '')

        # Check if we have context data for this owner
        for celebrity_name, tails in CELEBRITY_CONTEXT.items():
            if celebrity_name in owner and tail in tails:
                aircraft['context'] = tails[tail]
                print(f"✓ Added context for {owner} ({tail})")
                updated += 1
                break

    print(f"\n✓ Enhanced {updated} aircraft with context data")
    return data

def main():
    print("Enhancing aircraft_list.json with celebrity context data...\n")

    data = load_aircraft_list()
    data = add_context_data(data)
    save_aircraft_list(data)

    print("\nDone! Aircraft list enhanced with:")
    print("  - Net worth information")
    print("  - Aircraft values")
    print("  - Performance specs (range, speed, passengers)")
    print("  - Fascinating facts")
    print("  - Wikipedia links")

if __name__ == '__main__':
    main()
