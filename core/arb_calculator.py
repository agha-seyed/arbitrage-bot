class ArbCalculator:
    """
    محاسبه آربیتراژها از روی دیتای خام.
    """
    
    def find_all(self, games: list) -> list:
        opportunities = []
        
        for game in games:
            event_id = game.get("id", "")
            sport_key = game.get("sport_key", "")
            commence_time = game.get("commence_time", "")
            home_team = game.get("home_team", "")
            away_team = game.get("away_team", "")
            bookmakers = game.get("bookmakers", [])
            
            best_h2h = {"home": {"price": 0, "bookie": ""}, "away": {"price": 0, "bookie": ""}, "draw": {"price": 0, "bookie": ""}}
            best_totals = {}
            best_spreads = {}
            
            for book in bookmakers:
                bookie_name = book["key"]
                
                for market in book.get("markets", []):
                    if market["key"] == "h2h":
                        for outcome in market.get("outcomes", []):
                            if outcome["name"] == home_team and outcome["price"] > best_h2h["home"]["price"]:
                                best_h2h["home"] = {"price": outcome["price"], "bookie": bookie_name, "outcome_name": outcome["name"]}
                            elif outcome["name"] == away_team and outcome["price"] > best_h2h["away"]["price"]:
                                best_h2h["away"] = {"price": outcome["price"], "bookie": bookie_name, "outcome_name": outcome["name"]}
                            elif outcome["name"] == "Draw" and outcome["price"] > best_h2h["draw"]["price"]:
                                best_h2h["draw"] = {"price": outcome["price"], "bookie": bookie_name, "outcome_name": outcome["name"]}
                                
                    elif market["key"] == "totals":
                        for outcome in market.get("outcomes", []):
                            point = outcome.get("point")
                            if not point: continue
                            if point not in best_totals:
                                best_totals[point] = {"Over": {"price": 0, "bookie": ""}, "Under": {"price": 0, "bookie": ""}}
                            
                            name = outcome["name"]
                            if name in ["Over", "Under"] and outcome["price"] > best_totals[point][name]["price"]:
                                best_totals[point][name] = {"price": outcome["price"], "bookie": bookie_name, "outcome_name": name, "point": point}
                                
                    elif market["key"] == "spreads":
                        for outcome in market.get("outcomes", []):
                            point = outcome.get("point")
                            if not point: continue
                            
                            # Create nested dict for the specific point line
                            if point not in best_spreads:
                                best_spreads[point] = {home_team: {"price": 0, "bookie": ""}, away_team: {"price": 0, "bookie": ""}}
                                
                            name = outcome["name"]
                            if name in [home_team, away_team] and outcome["price"] > best_spreads[point][name]["price"]:
                                best_spreads[point][name] = {"price": outcome["price"], "bookie": bookie_name, "outcome_name": name, "point": point}
            
            # بررسی H2H
            h_price, a_price, d_price = best_h2h["home"]["price"], best_h2h["away"]["price"], best_h2h["draw"]["price"]
            if h_price > 1 and a_price > 1:
                ip = 1/h_price + 1/a_price
                has_draw = False
                if d_price > 1:
                    ip += 1/d_price
                    has_draw = True
                
                if ip < 1:
                    profit_pct = (1 - ip) * 100
                    legs = [
                        {"bookmaker": best_h2h["home"]["bookie"], "market": "h2h", "outcome": best_h2h["home"]["outcome_name"], "odd": h_price},
                        {"bookmaker": best_h2h["away"]["bookie"], "market": "h2h", "outcome": best_h2h["away"]["outcome_name"], "odd": a_price}
                    ]
                    if has_draw:
                        legs.append({"bookmaker": best_h2h["draw"]["bookie"], "market": "h2h", "outcome": best_h2h["draw"]["outcome_name"], "odd": d_price})
                        
                    opportunities.append({
                        "event_id": event_id,
                        "sport_key": sport_key,
                        "commence_time": commence_time,
                        "event_name": f"{home_team} vs {away_team}",
                        "profit_pct": profit_pct,
                        "market_type": "H2H",
                        "legs": legs
                    })
                    
            # بررسی Totals
            for point, data in best_totals.items():
                o_price, u_price = data["Over"]["price"], data["Under"]["price"]
                if o_price > 1 and u_price > 1:
                    ip = 1/o_price + 1/u_price
                    if ip < 1:
                        profit_pct = (1 - ip) * 100
                        opportunities.append({
                            "event_id": event_id,
                            "sport_key": sport_key,
                            "commence_time": commence_time,
                            "event_name": f"{home_team} vs {away_team} (O/U {point})",
                            "profit_pct": profit_pct,
                            "market_type": "Totals",
                            "legs": [
                                {"bookmaker": data["Over"]["bookie"], "market": "totals", "outcome": "Over", "odd": o_price},
                                {"bookmaker": data["Under"]["bookie"], "market": "totals", "outcome": "Under", "odd": u_price}
                            ]
                        })
                        
            # بررسی Spreads (Asian Handicap)
            for point, data in best_spreads.items():
                h_price, a_price = data[home_team]["price"], data[away_team]["price"]
                if h_price > 1 and a_price > 1:
                    ip = 1/h_price + 1/a_price
                    if ip < 1:
                        profit_pct = (1 - ip) * 100
                        opportunities.append({
                            "event_id": event_id,
                            "sport_key": sport_key,
                            "commence_time": commence_time,
                            "event_name": f"{home_team} vs {away_team} (AH {point})",
                            "profit_pct": profit_pct,
                            "market_type": "Spreads",
                            "legs": [
                                {"bookmaker": data[home_team]["bookie"], "market": "spreads", "outcome": home_team, "odd": h_price},
                                {"bookmaker": data[away_team]["bookie"], "market": "spreads", "outcome": away_team, "odd": a_price}
                            ]
                        })
                        
        return opportunities
