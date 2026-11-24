MY_EXAMPLES = [
    # --- her own three ---
    ("me dancing and roz bouncing next to me", "av=dance1;fx=bounce;t=roz"),
    ("hi!! in cute pink and sparlkes", "fg=FF9CC8;bp=sparkles;st=outline;t=hi!!"),
    ("me with curly hair gving a kiss face", "av=ooh;hr=curly;t="),

    # --- mini me faces + hair ---
    ("me smiling w straight hair", "av=smile;hr=straight;t="),
    ("just me smiling", "av=smile;t="),
    ("me with my bunny teeth out lol", "av=teeth;t="),
    ("lil me showing my teeth", "av=teeth;t="),
    ("me making a kissy face", "av=ooh;t="),
    ("me blowing kisses with straight hair", "av=ooh;hr=straight;t="),
    ("me going ooh", "av=ooh;t="),
    ("me grinning so big", "av=grin;t="),
    ("me being so happy", "av=grin;t="),
    ("me just chillin", "av=chill;t="),
    ("me lookin unbothered", "av=chill;t="),
    ("chill me with curly hair", "av=chill;hr=curly;t="),

    # --- mini me dances ---
    ("me dancing", "av=dance1;t="),
    ("me dancing w my curls", "av=dance1;hr=curly;t="),
    ("me doing dance 2", "av=dance2;t="),
    ("me doing the second dance with straight hair", "av=dance2;hr=straight;t="),
    ("me doing dance 3 fast", "av=dance3;sp=3;t="),
    ("me jumping around", "av=dance3;t="),
    ("me dancing slow", "av=dance1;sp=1;t="),
    ("me shuffling", "av=dance2;t="),

    # --- me + words ---
    ("me dancing and roz bouncing", "av=dance1;fx=bounce;t=roz"),
    ("me dancing next to ROZ", "av=dance1;t=ROZ"),
    ("ROZ with me dancing", "av=dance1;t=ROZ"),
    ("me grinning and PLUR", "av=grin;t=PLUR"),
    ("me saying hi", "av=smile;t=hi"),
    ("me saying HI!! with my teeth out", "av=teeth;t=HI!!"),
    ("me blowing a kiss and xoxo", "av=ooh;t=xoxo"),
    ("me doing dance 2 and FISHER in green", "av=dance2;fg=8FE36B;t=FISHER"),
    ("kiss face me with LOVE U", "av=ooh;t=LOVE U"),
    ("me chillin and good vibes", "av=chill;t=good vibes"),

    # --- names (fixes "show my name ALEXIA") ---
    ("show my name ALEXIA", "t=ALEXIA"),
    ("my name ALEXIA in pink", "fg=FF9CC8;t=ALEXIA"),
    ("put my name alexia", "t=alexia"),
    ("write my name LEXI", "t=LEXI"),
    ("my name is ALEXIA", "t=ALEXIA"),
    ("my bestie's name MAYA", "t=MAYA"),

    # --- ROZ ---
    ("roz", "t=roz"),
    ("ROZ invert colors fast", "fx=invert;sp=3;t=ROZ"),
    ("roz flashing", "fx=invert;t=roz"),
    ("roz bouncing", "fx=bounce;t=roz"),
    ("roz but make it cute", "fx=bounce;st=outline;fg=FFFFFF;ac=FF2FA0;bg=FF9CC8;bp=hearts;t=roz"),
    ("roz glitchy and green", "fx=glitch;fg=8FE36B;bg=000000;t=roz"),
    ("ROZ in yellow on black flashing", "fx=invert;fg=FFE14D;bg=000000;t=ROZ"),
    ("i love roz with hearts", "bp=hearts;t=i love roz"),
    ("I LOVE ROZ in hot pink bubble letters", "fg=FF2FA0;st=outline;t=I LOVE ROZ"),
    ("roz roz roz rainbow", "fx=rainbow;t=roz roz roz"),

    # --- cute / pink / sparkles ---
    ("hi!! in cute pink", "fg=FF9CC8;st=outline;t=hi!!"),
    ("hii in pink with sparkles", "fg=FF9CC8;bp=sparkles;t=hii"),
    ("plur in cute bubble letters", "st=outline;t=plur"),
    ("xoxo with hearts everywhere", "bp=hearts;t=xoxo"),
    ("kandi kid in pastel pink", "fg=FF9CC8;t=kandi kid"),
    ("cute pink hearts bg", "bp=hearts;b2=FF9CC8;t="),
    ("sparkly purple bg", "bp=sparkles;bg=A06BFF;t="),
    ("sparlkes on black", "bp=sparkles;bg=000000;t="),
    ("lilac sparkles", "bp=sparkles;b2=C9B5FF;t="),
    ("bestie in lavender with stars", "fg=C9B5FF;bp=stars;t=bestie"),

    # --- effects with typos + slang ---
    ("TECHNO glitchy fr", "fx=glitch;t=TECHNO"),
    ("bass wavy and slow", "fx=wave;sp=1;t=bass"),
    ("drop it bouncin", "fx=bounce;t=drop it"),
    ("rave in rainbow letters", "fx=rainbow;t=rave"),
    ("hydrate pulsing", "fx=pulse;t=hydrate"),
    ("free hugs typewriter", "fx=type;t=free hugs"),
    ("lets gooo scrolling fast", "fx=scroll;sp=3;t=lets gooo"),
    ("SLAY flashing super fast", "fx=invert;sp=3;t=SLAY"),
    ("omg wiggly", "fx=wave;t=omg"),
    ("wubs glitch fast green", "fx=glitch;sp=3;fg=8FE36B;t=wubs"),
    ("dom dolla scrollin", "fx=scroll;t=dom dolla"),
    ("sara landry flashing on black", "fx=invert;bg=000000;t=sara landry"),
    ("john summit in orange on navy", "fg=FF9A3C;bg=2F3A9E;t=john summit"),

    # --- backgrounds + colors ---
    ("PLUR on a checkered bg", "bp=checker;t=PLUR"),
    ("peace with stripes", "bp=stripes;t=peace"),
    ("love on polka dots", "bp=dots;t=love"),
    ("vibes with a rainbow background", "bp=rainbow;t=vibes"),
    ("starry night sky with HI", "bp=stars;t=HI"),
    ("pink to purple gradient", "bp=gradient;bg=FF9CC8;b2=A06BFF;t="),
    ("lavender gradient", "bp=gradient;bg=C9B5FF;t="),
    ("baby blue bg with white text BASS", "bg=5AA8FF;fg=FFFFFF;t=BASS"),
    ("trance in mint on black", "fg=7DFFC8;bg=000000;t=trance"),

    # --- vibes ---
    ("spooky vibes BOO", "fx=glitch;fg=FF9A3C;ac=000000;bg=000000;b2=A06BFF;bp=stars;t=BOO"),
    ("cute PLUR", "fx=bounce;st=outline;fg=FFFFFF;ac=FF2FA0;bg=FF9CC8;b2=FFFFFF;bp=hearts;t=PLUR"),
    ("galaxy vibes with me chilling", "fx=pulse;fg=C9B5FF;ac=A06BFF;bg=1A0033;b2=FFFFFF;bp=stars;av=chill;t="),
    ("techno vibes HEADBANG", "fx=glitch;st=plain;fg=7DFFC8;ac=FF2FA0;bg=000000;b2=2F3A9E;bp=stripes;t=HEADBANG"),

    # --- everything at once ---
    ("me dancing and roz bouncing next to me in pink with sparkles", "av=dance1;fx=bounce;fg=FF9CC8;bp=sparkles;t=roz"),
    ("me with curly hair giving a kiss face and xoxo on hearts", "av=ooh;hr=curly;bp=hearts;t=xoxo"),
    ("hi!! in cute pink and sparkles with me smiling", "fg=FF9CC8;bp=sparkles;st=outline;av=smile;t=hi!!"),
    ("me doing dance 3 and TECHNO glitchy on black", "av=dance3;fx=glitch;bg=000000;t=TECHNO"),
    ("roz flashing fast and me grinning", "fx=invert;sp=3;av=grin;t=roz"),
]
