from filters.bookmaker_classifier import BookmakerClassifier

def test():
    clf = BookmakerClassifier()
    
    # آربیتراژ soft vs soft — باید HIGH باشد
    opp_high = {
        "legs": [
            {"bookmaker": "snai"},
            {"bookmaker": "eurobet"}
        ]
    }
    result = clf.evaluate(opp_high)
    assert result['quality'] == 'HIGH', f"❌ باید HIGH باشد، گرفت: {result['quality']}"
    print(f"✅ soft vs soft → HIGH ({result['emoji']})")
    
    # آربیتراژ sharp vs soft — باید MEDIUM باشد
    opp_medium = {
        "legs": [
            {"bookmaker": "pinnacle"},
            {"bookmaker": "snai"}
        ]
    }
    result = clf.evaluate(opp_medium)
    assert result['quality'] == 'MEDIUM', f"❌ باید MEDIUM باشد"
    print(f"✅ sharp vs soft → MEDIUM ({result['emoji']})")
    
    # آربیتراژ sharp vs sharp — باید LOW باشد و recommended=False
    opp_low = {
        "legs": [
            {"bookmaker": "pinnacle"},
            {"bookmaker": "betfair_ex"}
        ]
    }
    result = clf.evaluate(opp_low)
    assert result['quality'] == 'LOW', f"❌ باید LOW باشد"
    assert result['recommended'] == False, "❌ recommended باید False باشد"
    print(f"✅ sharp vs sharp → LOW — block شد ({result['emoji']})")
    
    print("✅ BookmakerClassifier درست کار میکند")

if __name__ == "__main__":
    test()
