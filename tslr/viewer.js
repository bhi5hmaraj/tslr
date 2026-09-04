// TS 11/14/18 massing viewer. Three parts, in dependency order:
//   Geom    the construction, pure functions, no DOM
//   Render  geometry -> SVG
//   UI      controls and wiring
// The plot corners and the test vectors are substituted in by tslr/html.py.

const SITE = __SITE__;


// ---------------------------------------------------------------- I18N
// Every string the reader sees, in both languages. Tamil is the working
// language on site in Madurai; English is what the FMB extract is written in.
const I18N = {
  en: {
    lang: "தமிழ்", boundary: "Boundary, metres — edit to try other figures",
    north: "north", east: "east", south: "south", west: "west",
    diagonal: "diagonal A–C",
    roadLabel: "Road width, perpendicular to the north boundary",
    splitLabel: "Split the rectangle", oneRect: "one rectangle",
    lots: n => `${n} equal lots`, metres: "metres",
    turnLabel: "Turn the block off the south boundary",
    squareOn: "square to AB", bestBtn: "best",
    offcut: n => `Offcut ${n}`,
    turnNote: (a, d) => `Largest rectangle at ${a}° inside the land the road ` +
      `leaves. ${d}` ,
    turnGain: (g, c) => `${g > 0 ? "+" : ""}${g.toLocaleString()} ft² ` +
      `(${g > 0 ? "+" : ""}${c} cents) against squaring it to the south boundary.`,
    turnExplain: "Step-by-step covers the squared construction — set the turn " +
                 "back to 0° to walk through it.",
    fanLabel: "Four-sided lots — no waste at all",
    eqLabel: "Give every lot the same buildable rectangle",
    entrance: "opens onto the road over",
    beyondRay: "of which, past the ray, serving only the dead end:",
    headLabel: "Turning head at the dead end, back along the road from E",
    headOff: "none", TurningHead: "Turning head",
    headNote: (l, d, a, c) => `A car turning at the dead end needs ${l} ft back ` +
      `along the road from E, then ${d} ft square down to the east boundary. ` +
      `That right triangle is ${a} ft² (${c} cents) of common ground, taken ` +
      `off the last lot before the others are cut.`,
    wedgeNote: (yc, ly, a, c) => `Carried on across the road the same ray meets ` +
      `the north boundary at Y, so YC = ${yc} ft and LY = ${ly} ft. Everything ` +
      `east of the ray is the right triangle LYC: ${a} ft² (${c} cents), the ` +
      `dead end of the layout.`,
    noFront: "no road frontage — reached across the strip in front, which is " +
             "therefore common, not private",
    buildable: "buildable",
    eqNote: (a, c) => `Cuts set so the largest rectangle inside every lot is the ` +
      `same: ${a} ft² (${c} cents) each. The corner lot gets more land to make ` +
      `up for the wedge it cannot build on.`,
    fanNote: (a, c, w) => `Cut straight across the land the road leaves, square ` +
      `to the road. Nothing is left over. Each lot ${a} ft² (${c} cents), ` +
      `${w} ft² more per lot than rectangles squared to the south boundary.`,
    fanCorner: d => `The corner lot's sharpest angle is ${d}°.`,
    explainBtn: "Explain this construction", backBtn: "← back to the plan",
    closure: "closure", slants: "north boundary slants",
    footer: "Road runs the full north boundary D→C; its inner edge meets the west " +
            "boundary at F and the east at E. The rectangle stands square to the " +
            "south boundary and rises until it meets that edge.",
    registered: "Registered extent", cannot: "Cannot draw these figures",
    noRoom: "no room for that road",
    thPiece: "piece", thSides: "sides, and area = base × height",
    thCents: "cents", tally: "TALLY", partsSum: "parts sum to the plot",
    partsDont: "PARTS DO NOT SUM",
    Road: "Road", Rectangle: "Rectangle", lot: n => `Lot ${n}`,
    "T1 under the road": "T1", "T2 west corner": "T2 west",
    "T3 east corner": "T3 east",
    checkPass: n => `self-check passed — ${n} road widths`,
    checkFail: w => "self-check FAILED: " + w,
    checkEdited: "sides edited — self-check applies to the recorded plot only",
    working: "How each number is got, from the four recorded sides:",
    ofPlot: "of the plot",
    fit: "fit", pdfBtn: "PDF",
    scaleBar: (m2, s) => `100 mm on this sheet = ${m2} m on the ground  (1:${s})`,
    legendHead: s => `Measurements, feet — drawing at 1:${s}`,
    diagTaped: "Ours was taped on site.",
    diagGuessed: "Ours is <b>not yet taped</b> — it comes from four corners read " +
                 "off satellite imagery, good to about ±1.2 m, which is ±17 m² of " +
                 "area. A tape on AC would settle it.",
    noTriangle: (a, b, c) => `no triangle with sides ${a}, ${b}, ${c}`,
    badSide: (i, got, want) => `closure side ${i} came out ${got} m, not ${want}`,
    steps: [
      { t: v => "Close the boundary",
        b: v => `Four sides do not fix a quadrilateral — they hinge, and the FMB
          records only four. <b>AC is not derived from them: it is a fifth,
          independent measurement.</b> ${v.diagSrc} Given it, the plot is two
          triangles glued along AC, each solved from three known sides, and
          everything below is measured off the four corners that fall out.` },
      { t: v => "The north boundary is not parallel to the south",
        b: v => `DC runs <b>${v.slant}°</b> off AB. That single fact is why a
          rectangle cannot fill this plot, and it is where every offcut below
          comes from.` },
      { t: v => `Set the road back ${v.road}`,
        b: v => `Offset DC inward by ${v.road}, measured perpendicular. The offset
          line meets the west boundary at <b>F</b> and the east at <b>E</b>, giving
          <b>DF = ${v.df}</b> and <b>EC = ${v.ec}</b>. DF is close to the road width
          because the corner at D is ${v.dAngle}° — nearly square; EC is longer
          because C is sharp.` },
      { t: v => "Square the rectangle to the south boundary",
        b: v => `Drop a perpendicular from F to AB, meeting it at <b>G</b>, so
          <b>AG = ${v.ag}</b>. West of G the plot leans away and no rectangle can
          reach it. The rectangle runs <b>GB = ${v.gb}</b>.` },
      { t: v => "Raise it until it meets the road",
        b: v => `Square to the south boundary the plot is <b>${v.hE}</b> deep at B
          and <b>${v.hW}</b> at F, so the east end binds. The road takes
          <b>${v.drop}</b> of that, not ${v.road}: ${v.road} is measured square to
          DC, and DC is tilted ${v.slant}° to the line we are measuring down from,
          so ${v.road} ÷ cos ${v.slant}° = ${v.drop}. That leaves
          <b>${v.hE} − ${v.drop} = ${v.bh}</b> — the depth, all the way along.` },
      { t: v => "T1 — the price of the slant",
        b: v => `Base <b>JH = ${v.jh}</b>, the rectangle's flat top. The height
          <b>JF = ${v.jf}</b> is simply how far the road's underside falls across
          that width: it is ${v.jf} higher above the south boundary at the west end
          than at the east, which is what the ${v.slant}° tilt costs over ${v.jh}.
          JF is square to JH, so <b>½ × ${v.jh} × ${v.jf} = ${v.t1a} ft²</b>.` },
      { t: v => "T2 — the west corner",
        b: v => `Base <b>AG = ${v.ag}</b> — how far the west boundary leans in
          over F's height. Height <b>GF = ${v.gf}</b>, the perpendicular that put G
          there; G, J and F sit on one line, so it is just the rectangle plus T1:
          ${v.bh} + ${v.jf}. <b>½ × ${v.ag} × ${v.gf} = ${v.t2a} ft²</b>.` },
      { t: v => "T3 — the east corner",
        b: v => `Base <b>BH = ${v.bh}</b>, the rectangle's east edge. The height
          <b>${v.t3h}</b> is how far E lies east of that edge, measured square to
          it — the width the plot gains between B and the road, which no rectangle
          squared to the south can reach. <b>½ × ${v.bh} × ${v.t3h} =
          ${v.t3a} ft²</b>.` },
      { t: v => "Add it back up",
        b: v => `Every piece is a rectangle, a trapezoid or a triangle, so every
          area is one multiplication. They sum to <b>${v.total} ft²</b> — the whole
          plot. If they did not, one of the steps above would be wrong.` },
    ],
  },
  ta: {
    lang: "English", boundary: "எல்லை அளவுகள், மீட்டரில் — மாற்றி பார்க்கலாம்",
    north: "வடக்கு", east: "கிழக்கு", south: "தெற்கு", west: "மேற்கு",
    diagonal: "மூலைவிட்டம் A–C",
    roadLabel: "சாலை அகலம், வடக்கு எல்லைக்கு செங்குத்தாக",
    splitLabel: "செவ்வகத்தைப் பிரி", oneRect: "ஒரே செவ்வகம்",
    lots: n => `${n} சம மனைகள்`, metres: "மீட்டர்",
    turnLabel: "தெற்கு எல்லையிலிருந்து தொகுதியைத் திருப்பு",
    squareOn: "AB க்கு நேராக", bestBtn: "சிறந்தது",
    offcut: n => `மீதி ${n}`,
    turnNote: (a, d) => `சாலை விட்டுச் செல்லும் நிலத்தில் ${a}° கோணத்தில் ` +
      `பொருந்தும் மிகப்பெரிய செவ்வகம். ${d}`,
    turnGain: (g, c) => `தெற்கு எல்லைக்கு நேராக வைப்பதை விட ` +
      `${g > 0 ? "+" : ""}${g.toLocaleString()} ச.அடி (${g > 0 ? "+" : ""}${c} சென்ட்).`,
    turnExplain: "படிப்படியான விளக்கம் நேரான அமைப்புக்கு மட்டுமே — திருப்பத்தை " +
                 "0° ஆக்கினால் அதைப் பார்க்கலாம்.",
    fanLabel: "நான்கு பக்க மனைகள் — வீணாவது எதுவும் இல்லை",
    eqLabel: "எல்லா மனைகளுக்கும் ஒரே கட்டிட செவ்வகம்",
    entrance: "சாலைக்கான நுழைவு அகலம்",
    beyondRay: "இதில், கதிருக்கு அப்பால், முட்டுச்சந்துக்கு மட்டும்:",
    headLabel: "முட்டுச்சந்தில் வாகனம் திரும்பும் இடம், E இலிருந்து சாலை வழியே",
    headOff: "இல்லை", TurningHead: "திரும்பும் இடம்",
    headNote: (l, d, a, c) => `முட்டுச்சந்தில் வாகனம் திரும்ப E இலிருந்து ${l} அடி ` +
      `சாலை வழியே, பின் ${d} அடி செங்குத்தாக கிழக்கு எல்லை வரை தேவை. அந்த ` +
      `செங்கோண முக்கோணம் ${a} ச.அடி (${c} சென்ட்) பொது இடம்.`,
    wedgeNote: (yc, ly, a, c) => `அதே கதிர் சாலையைக் கடந்து வடக்கு எல்லையை Y இல் ` +
      `சந்திக்கிறது: YC = ${yc} அடி, LY = ${ly} அடி. கதிருக்குக் கிழக்கே உள்ள ` +
      `அனைத்தும் LYC செங்கோண முக்கோணம்: ${a} ச.அடி (${c} சென்ட்).`,
    noFront: "சாலை முகப்பு இல்லை — முன்பகுதி வழியாகச் செல்ல வேண்டும், " +
             "எனவே அது பொது இடம்",
    buildable: "கட்டிடத்திற்கு",
    eqNote: (a, c) => `ஒவ்வொரு மனையிலும் பொருந்தும் மிகப்பெரிய செவ்வகம் ஒரே ` +
      `அளவாக இருக்கும்படி வெட்டப்பட்டது: தலா ${a} ச.அடி (${c} சென்ட்). மூலை மனைக்கு ` +
      `கட்ட முடியாத பகுதிக்கு ஈடாக அதிக நிலம் கிடைக்கிறது.`,
    fanNote: (a, c, w) => `சாலை விட்டுச் செல்லும் நிலத்தை சாலைக்கு நேராக ` +
      `நேர்க்கோட்டில் வெட்டியது. மீதம் எதுவும் இல்லை. ஒவ்வொரு மனையும் ${a} ச.அடி ` +
      `(${c} சென்ட்), தெற்கு எல்லைக்கு நேரான செவ்வகங்களை விட ${w} ச.அடி அதிகம்.`,
    fanCorner: d => `மூலை மனையின் கூர்மையான கோணம் ${d}°.`,
    explainBtn: "இந்த அமைப்பை விளக்கு", backBtn: "← வரைபடத்திற்குத் திரும்பு",
    closure: "மொத்த அளவு", slants: "வடக்கு எல்லையின் சாய்வு",
    footer: "சாலை வடக்கு எல்லை முழுவதும் D→C செல்கிறது; அதன் உட்புற விளிம்பு மேற்கு " +
            "எல்லையை F இலும் கிழக்கை E இலும் சந்திக்கிறது. செவ்வகம் தெற்கு எல்லைக்கு " +
            "செங்குத்தாக நின்று அந்த விளிம்பைத் தொடும் வரை உயர்கிறது.",
    registered: "பதிவு செய்யப்பட்ட பரப்பளவு", cannot: "இந்த அளவுகளை வரைய முடியாது",
    noRoom: "அந்த அகலமான சாலைக்கு இடம் இல்லை",
    thPiece: "பகுதி", thSides: "பக்கங்கள், பரப்பு = அடிப்படை × உயரம்",
    thCents: "சென்ட்", tally: "மொத்தம்", partsSum: "பகுதிகளின் கூட்டுத்தொகை சரி",
    partsDont: "பகுதிகள் கூடவில்லை",
    Road: "சாலை", Rectangle: "செவ்வகம்", lot: n => `மனை ${n}`,
    "T1 under the road": "T1", "T2 west corner": "T2 மேற்கு",
    "T3 east corner": "T3 கிழக்கு",
    checkPass: n => `சுய சரிபார்ப்பு சரி — ${n} சாலை அகலங்கள்`,
    checkFail: w => "சுய சரிபார்ப்பு தவறு: " + w,
    checkEdited: "பக்க அளவுகள் மாற்றப்பட்டன — சுய சரிபார்ப்பு பதிவு அளவுகளுக்கு மட்டுமே",
    working: "பதிவான நான்கு பக்க அளவுகளிலிருந்து ஒவ்வொரு எண்ணும் எப்படி வருகிறது:",
    ofPlot: "நிலத்தில்",
    lots: n => `${n} சம மனைகள்`, metres: "மீட்டர்",
    scaleBar: (m2, s) => `இத்தாளில் 100 மி.மீ = தரையில் ${m2} மீ  (1:${s})`,
    legendHead: s => `அளவுகள், அடியில் — வரைபடம் 1:${s}`,
    diagTaped: "நமது அளவு தரையில் நாடாவால் அளக்கப்பட்டது.",
    diagGuessed: "நமது அளவு <b>இன்னும் நாடாவால் அளக்கப்படவில்லை</b> — செயற்கைக்கோள் " +
                 "படத்திலிருந்து படித்த நான்கு மூலைகளிலிருந்து வந்தது, சுமார் ±1.2 மீ " +
                 "துல்லியம், அதாவது ±17 ச.மீ பரப்பு. AC ஐ நாடாவால் அளந்தால் இது தீரும்.",
    noTriangle: (a, b, c) => `${a}, ${b}, ${c} பக்கங்களுடன் முக்கோணம் அமையாது`,
    badSide: (i, got, want) => `எல்லை ${i} ${got} மீ ஆக வந்தது, ${want} அல்ல`,
    steps: [
      { t: v => "எல்லையை மூடுதல்",
        b: v => `நான்கு பக்க அளவுகள் மட்டும் ஒரு நாற்கரத்தை நிர்ணயிக்காது — அது
          மடங்கும்; FMB இல் நான்கு பக்கங்கள் மட்டுமே பதிவாகியுள்ளன. <b>AC அவற்றிலிருந்து
          கணக்கிடப்படவில்லை: அது ஐந்தாவது, தனி அளவீடு.</b> ${v.diagSrc} அது கிடைத்தால்,
          நிலம் AC ஐ ஒட்டிய இரு முக்கோணங்கள் ஆகும்; ஒவ்வொன்றும் மூன்று தெரிந்த
          பக்கங்களால் தீர்க்கப்படுகிறது, கீழே உள்ள அனைத்தும் அதிலிருந்து வரும் நான்கு
          மூலைகளிலிருந்து அளக்கப்படுகிறது.` },
      { t: v => "வடக்கு எல்லை தெற்குக்கு இணையாக இல்லை",
        b: v => `DC ஆனது AB இலிருந்து <b>${v.slant}°</b> சாய்கிறது. இந்த ஒரு
          காரணத்தால்தான் ஒரு செவ்வகம் இந்த நிலத்தை முழுமையாக நிரப்ப முடியாது; கீழே
          வரும் ஒவ்வொரு மீதிப் பகுதியும் இதிலிருந்தே வருகிறது.` },
      { t: v => `சாலைக்கு ${v.road} விடுதல்`,
        b: v => `DC இலிருந்து செங்குத்தாக ${v.road} உள்நோக்கி நகர்த்துக. அந்தக் கோடு
          மேற்கு எல்லையை <b>F</b> இலும் கிழக்கை <b>E</b> இலும் சந்திக்கிறது; இதனால்
          <b>DF = ${v.df}</b>, <b>EC = ${v.ec}</b>. D மூலை ${v.dAngle}° — கிட்டத்தட்ட
          செங்கோணம், எனவே DF சாலை அகலத்திற்கு நெருக்கமாக உள்ளது; C கூர்மையானது என்பதால்
          EC நீளமாக உள்ளது.` },
      { t: v => "தெற்கு எல்லைக்கு செங்குத்தாக செவ்வகம்",
        b: v => `F இலிருந்து AB க்கு செங்குத்துக் கோடு இறக்கினால் அது <b>G</b> இல்
          சந்திக்கிறது; எனவே <b>AG = ${v.ag}</b>. G க்கு மேற்கே நிலம் விலகிச் செல்வதால்
          எந்தச் செவ்வகமும் அங்கு எட்டாது. செவ்வகத்தின் அடிப்படை <b>GB = ${v.gb}</b>.` },
      { t: v => "சாலையைத் தொடும் வரை உயர்த்துதல்",
        b: v => `தெற்கு எல்லைக்கு செங்குத்தாக அளந்தால் B இல் நிலத்தின் ஆழம்
          <b>${v.hE}</b>, F இல் <b>${v.hW}</b> — எனவே கிழக்கு முனையே கட்டுப்படுத்துகிறது.
          சாலை அதில் <b>${v.drop}</b> எடுக்கிறது, ${v.road} அல்ல: ${v.road} என்பது DC க்கு
          செங்குத்தாக அளக்கப்படுகிறது, DC ஆனது நாம் அளக்கும் கோட்டிற்கு ${v.slant}°
          சாய்ந்துள்ளது, எனவே ${v.road} ÷ cos ${v.slant}° = ${v.drop}. மீதம்
          <b>${v.hE} − ${v.drop} = ${v.bh}</b> — இதுவே ஆழம், முழு நீளத்திற்கும்.` },
      { t: v => "T1 — சாய்வுக்கான விலை",
        b: v => `அடிப்படை <b>JH = ${v.jh}</b>, செவ்வகத்தின் தட்டையான மேற்பகுதி. உயரம்
          <b>JF = ${v.jf}</b> என்பது அந்த அகலத்தில் சாலையின் அடிப்பகுதி எவ்வளவு
          இறங்குகிறது என்பதே: மேற்கு முனையில் தெற்கு எல்லையிலிருந்து ${v.jf} அதிக
          உயரம் — ${v.jh} நீளத்தில் ${v.slant}° சாய்வின் விலை. JF ஆனது JH க்கு
          செங்குத்து, எனவே <b>½ × ${v.jh} × ${v.jf} = ${v.t1a} ச.அடி</b>.` },
      { t: v => "T2 — மேற்கு மூலை",
        b: v => `அடிப்படை <b>AG = ${v.ag}</b> — F இன் உயரத்திற்குள் மேற்கு எல்லை
          எவ்வளவு உள்நோக்கி சாய்கிறது என்பது. உயரம் <b>GF = ${v.gf}</b>, G ஐ
          உருவாக்கிய அதே செங்குத்துக் கோடு; G, J, F ஒரே கோட்டில் இருப்பதால் இது
          செவ்வகம் மற்றும் T1 இன் கூட்டுத்தொகையே: ${v.bh} + ${v.jf}.
          <b>½ × ${v.ag} × ${v.gf} = ${v.t2a} ச.அடி</b>.` },
      { t: v => "T3 — கிழக்கு மூலை",
        b: v => `அடிப்படை <b>BH = ${v.bh}</b>, செவ்வகத்தின் கிழக்கு விளிம்பு. உயரம்
          <b>${v.t3h}</b> என்பது அந்த விளிம்பிற்கு கிழக்கே E எவ்வளவு தொலைவில் உள்ளது
          என்பது, செங்குத்தாக அளந்தால் — B க்கும் சாலைக்கும் இடையே நிலம் பெறும் அகலம்,
          தெற்குக்கு செங்குத்தான எந்தச் செவ்வகமும் அதை எட்டாது.
          <b>½ × ${v.bh} × ${v.t3h} = ${v.t3a} ச.அடி</b>.` },
      { t: v => "மொத்தத்தைச் சரிபார்த்தல்",
        b: v => `ஒவ்வொரு பகுதியும் செவ்வகம், சரிவகம் அல்லது முக்கோணம் — எனவே ஒவ்வொரு
          பரப்பளவும் ஒரே பெருக்கல். அவை கூடி <b>${v.total} ச.அடி</b> — முழு நிலமும்
          அவ்வளவே. கூடவில்லை என்றால் மேலே ஒரு படி தவறாகும்.` },
    ],
  },
};
let LANG = "en";
const T = (k, ...a) => {
  const v = (I18N[LANG] || I18N.en)[k] ?? I18N.en[k] ?? k;
  return typeof v === "function" ? v(...a) : v;
};

// ---------------------------------------------------------------- Geom
const Geom = {
  sub: (a, b) => [a[0] - b[0], a[1] - b[1]],
  add: (a, b) => [a[0] + b[0], a[1] + b[1]],
  mul: (a, k) => [a[0] * k, a[1] * k],
  dot: (a, b) => a[0] * b[0] + a[1] * b[1],
  dist: (a, b) => Math.hypot(b[0] - a[0], b[1] - a[1]),

  unit(a, b) {
    const d = Geom.sub(b, a), L = Math.hypot(d[0], d[1]);
    return [[d[0] / L, d[1] / L], L];
  },

  // perpendicular foot of p on the line a-b
  foot(p, a, b) {
    const [u] = Geom.unit(a, b), t = Geom.dot(Geom.sub(p, a), u);
    return Geom.add(a, Geom.mul(u, t));
  },

  // from p, perpendicular to a-b, out to the line c-d
  crossTo(p, a, b, c, d) {
    const [u] = Geom.unit(a, b), n = [-u[1], u[0]], [v] = Geom.unit(c, d);
    const t = ((c[0] - p[0]) * v[1] - (c[1] - p[1]) * v[0]) / (n[0] * v[1] - n[1] * v[0]);
    return Geom.add(p, Geom.mul(n, t));
  },

  // intersection of the infinite lines p1-p2 and p3-p4
  meet(p1, p2, p3, p4) {
    const d1 = Geom.sub(p2, p1), d2 = Geom.sub(p4, p3);
    const den = d1[0] * d2[1] - d1[1] * d2[0];
    const t = ((p3[0] - p1[0]) * d2[1] - (p3[1] - p1[1]) * d2[0]) / den;
    return Geom.add(p1, Geom.mul(d1, t));
  },

  // distance from p to the segment a-b
  ptSeg(p, a, b) {
    const d = Geom.sub(b, a), L2 = d[0] * d[0] + d[1] * d[1];
    if (L2 < 1e-12) return Geom.dist(p, a);
    const t = Math.max(0, Math.min(1, Geom.dot(Geom.sub(p, a), d) / L2));
    return Geom.dist(p, [a[0] + d[0] * t, a[1] + d[1] * t]);
  },

  // distance between two segments, 0 if they cross
  segDist([a, b], [c, d]) {
    const cross = (p, q, r) => (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]);
    const d1 = cross(a, b, c), d2 = cross(a, b, d);
    const d3 = cross(c, d, a), d4 = cross(c, d, b);
    if (d1 * d2 < 0 && d3 * d4 < 0) return 0;
    return Math.min(Geom.ptSeg(c, a, b), Geom.ptSeg(d, a, b),
                    Geom.ptSeg(a, c, d), Geom.ptSeg(b, c, d));
  },

  shoelace(pts) {
    let s = 0;
    for (let i = 0; i < pts.length; i++) {
      const j = (i + 1) % pts.length;
      s += pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1];
    }
    return Math.abs(s) / 2;
  },

  M2FT: 1 / 0.3048,

  // circle-circle intersection; `left` picks the side of p->q to land on.
  // Circles that cannot meet are refused: clamping would return a point that
  // looks fine and silently gives the wrong quadrilateral.
  meetR(p, r1, q, r2, left) {
    const [u, d] = Geom.unit(p, q);
    if (d > r1 + r2 + 1e-9 || d < Math.abs(r1 - r2) - 1e-9)
      throw new Error(T("noTriangle", d.toFixed(2), r1.toFixed(2), r2.toFixed(2)));
    const a = (r1 * r1 - r2 * r2 + d * d) / (2 * d);
    const h = Math.sqrt(Math.max(0, r1 * r1 - a * a));
    const s = left ? 1 : -1;
    return [p[0] + u[0] * a - s * u[1] * h, p[1] + u[1] * a + s * u[0] * h];
  },

  // Four sides do not fix a quadrilateral; four sides and a diagonal do. Two
  // triangles glued along the diagonal, each solved by circle intersection.
  // Sides in metres, corners out in feet.
  // The range a diagonal must fall in for both triangles to close.
  diagonalRange({ north, east, south, west }) {
    return [Math.max(Math.abs(south - east), Math.abs(north - west)),
            Math.min(south + east, north + west)];
  },

  closure({ north, east, south, west, diagonal, ends = "AC" }) {
    const A = [0, 0], B = [south, 0];
    let C, D;
    if (ends === "AC") {
      C = Geom.meetR(A, diagonal, B, east, true);
      D = Geom.meetR(A, west, C, north, true);
    } else {
      D = Geom.meetR(B, diagonal, A, west, false);
      C = Geom.meetR(B, east, D, north, false);
    }
    const out = [A, B, C, D].map(p => [p[0] * Geom.M2FT, p[1] * Geom.M2FT]);
    // The closure must carry the lengths it was given -- everything downstream
    // is measured off these corners.
    const want = [south, east, north, west];
    for (let i = 0; i < 4; i++) {
      const got = Geom.dist(out[i], out[(i + 1) % 4]) / Geom.M2FT;
      if (Math.abs(got - want[i]) > 0.01)
        throw new Error(T("badSide", i + 1, got.toFixed(2), want[i].toFixed(2)));
    }
    return out;
  },

  // The whole construction. corners = [A, B, C, D] in feet.
  // Keep the part of a convex polygon on one side of the line a->b: `want` is
  // +1 for the side `ref` lies on, -1 for the other. Sutherland-Hodgman.
  clipHalf(poly, a, b, ref, want) {
    const side = q => (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0]);
    const s0 = (Math.sign(side(ref)) || 1) * want;
    const inside = q => side(q) * s0 >= -1e-9;
    const out = [];
    for (let i = 0; i < poly.length; i++) {
      const p = poly[i], q = poly[(i + 1) % poly.length];
      if (inside(p)) out.push(p);
      if (inside(p) !== inside(q)) {
        const t = side(p) / (side(p) - side(q));
        out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]);
      }
    }
    return out.filter((q, i) => Geom.dist(q, out[(i + 1) % out.length]) > 1e-6);
  },

  // Largest rectangle with edges at `deg` inside a convex region. The lower
  // boundary of a convex region is convex and the upper is concave, so a
  // rectangle spanning [xa, xb] is as tall as the tighter of its two ends
  // allows. That leaves a 2-D search over the two ends: coarse, then refined.
  inscribe(region, deg, m = 110, rounds = 4) {
    const t = deg * Math.PI / 180;
    const rot = (pts, ang) => pts.map(([x, y]) =>
      [x * Math.cos(ang) - y * Math.sin(ang), x * Math.sin(ang) + y * Math.cos(ang)]);
    const xy = rot(region, -t);
    const lo = Math.min(...xy.map(q => q[0])), hi = Math.max(...xy.map(q => q[0]));
    const prof = x => {
      let a = Infinity, b = -Infinity;
      for (let i = 0; i < xy.length; i++) {
        const p = xy[i], q = xy[(i + 1) % xy.length];
        if (x < Math.min(p[0], q[0]) - 1e-9 || x > Math.max(p[0], q[0]) + 1e-9) continue;
        if (Math.abs(q[0] - p[0]) < 1e-12) {
          a = Math.min(a, p[1], q[1]); b = Math.max(b, p[1], q[1]);
        } else {
          const y = p[1] + (q[1] - p[1]) * (x - p[0]) / (q[0] - p[0]);
          a = Math.min(a, y); b = Math.max(b, y);
        }
      }
      return [a, b];
    };
    const lin = (x0, x1, k) => Array.from({ length: k }, (_, i) => x0 + (x1 - x0) * i / (k - 1));
    const bestOn = xs => {
      const pr = xs.map(prof);
      let best = [0, xs[0], xs[0], 0, 0];
      for (let i = 0; i < xs.length; i++)
        for (let j = i + 1; j < xs.length; j++) {
          const bot = Math.max(pr[i][0], pr[j][0]), top = Math.min(pr[i][1], pr[j][1]);
          const ar = (xs[j] - xs[i]) * Math.max(0, top - bot);
          if (ar > best[0]) best = [ar, xs[i], xs[j], bot, top];
        }
      return best;
    };
    let [area, xa, xb, y0, y1] = bestOn(lin(lo, hi, m));
    let span = (hi - lo) / m;
    for (let r = 0; r < rounds; r++) {
      const xs = [...lin(Math.max(lo, xa - span), Math.min(hi, xa + span), m / 2),
                  ...lin(Math.max(lo, xb - span), Math.min(hi, xb + span), m / 2)]
                 .sort((c, d) => c - d);
      [area, xa, xb, y0, y1] = bestOn(xs);
      span /= 6;
    }
    return { area, box: rot([[xa, y0], [xb, y0], [xb, y1], [xa, y1]], t) };
  },

  bestTurn(region) {
    let best = [-1, 0];
    for (let d = -90; d < 90; d += 1) best = Geom.max2(best, [Geom.inscribe(region, d).area, d]);
    for (const step of [0.25, 0.05, 0.01])
      for (const k of [-2, -1, 1, 2])
        best = Geom.max2(best, [Geom.inscribe(region, best[1] + k * step).area, best[1] + k * step]);
    // A rectangle turned by d and by d+90 is the same rectangle, so report the
    // representative near square rather than the quarter-turned twin.
    const d = ((best[1] + 45) % 90 + 90) % 90 - 45;
    return Math.round(d * 100) / 100;
  },

  max2: (a, b) => (b[0] > a[0] ? b : a),

  // What a convex region has outside a rectangle inside it: peel one of the
  // rectangle's four half-planes at a time, so the parts are disjoint and add
  // back to the region exactly.
  offcuts(region, box) {
    const c = box.reduce((a, q) => [a[0] + q[0] / 4, a[1] + q[1] / 4], [0, 0]);
    let rest = region;
    const out = [];
    for (let i = 0; i < 4; i++) {
      const a = box[i], b = box[(i + 1) % 4];
      const cut = Geom.clipHalf(rest, a, b, c, -1);
      if (Math.abs(Geom.shoelace(cut)) > 0.5) out.push(cut);
      rest = Geom.clipHalf(rest, a, b, c, 1);
    }
    return out.sort((p, q) => Math.abs(Geom.shoelace(q)) - Math.abs(Geom.shoelace(p)))
      .map((poly, i) => ({ key: `off${i + 1}`, nk: "offcut", ni: i + 1, poly,
                           why: Geom.fanWhy(poly), area: Math.abs(Geom.shoelace(poly)) }));
  },

  // n equal-area slices of a convex region, cut by straight lines square to the
  // direction a->b. Nothing is left over, so every square foot is in a lot.
  bands(region, a, b, n, equalise = "land") {
    const [u] = Geom.unit(a, b);
    const proj = q => (q[0] - a[0]) * u[0] + (q[1] - a[1]) * u[1];
    const ts = region.map(proj), lo = Math.min(...ts), hi = Math.max(...ts);
    const on = t => [a[0] + u[0] * t, a[1] + u[1] * t];
    const band = (t0, t1) => {
      const [p0, p1] = [on(t0), on(t1)];
      const perp = q => [q[0] - u[1], q[1] + u[0]];
      const g = Geom.clipHalf(region, p0, perp(p0), on(t0 + 10), 1);
      return Geom.clipHalf(g, p1, perp(p1), on(t1 - 10), 1);
    };
    const ang = Math.atan2(b[1] - a[1], b[0] - a[0]) * 180 / Math.PI;
    const whole = Math.abs(Geom.shoelace(region));
    // How much of a lot an architect can actually build on: the largest
    // rectangle inside it, set out square to the road the house will face.
    const buildable = g => g.length < 3 || Math.abs(Geom.shoelace(g)) < 1 ? 0
                         : Geom.inscribe(g, ang, 34, 3).area;
    let cuts;
    if (equalise === "buildable") {
      // Take each lot no wider than it needs to be. If that walk runs out of
      // land, no other set of cuts reaches this target either.
      const reach = want => {
        let prev = lo; const out = [];
        for (let i = 0; i < n - 1; i++) {
          if (buildable(band(prev, hi)) < want) return null;
          let c = prev, e = hi;
          for (let k = 0; k < 34; k++) {
            const mid = (c + e) / 2;
            if (buildable(band(prev, mid)) < want) c = mid; else e = mid;
          }
          out.push((c + e) / 2); prev = out[out.length - 1];
        }
        return buildable(band(prev, hi)) >= want ? out : null;
      };
      let c = 0, e = whole / n;
      for (let k = 0; k < 26; k++) {
        const mid = (c + e) / 2;
        if (reach(mid)) c = mid; else e = mid;
      }
      cuts = reach(c) || [];
    } else {
      cuts = [];
      for (let i = 1; i < n; i++) {
        let c = cuts.length ? cuts[cuts.length - 1] : lo, e = hi;
        for (let k = 0; k < 60; k++) {
          const mid = (c + e) / 2;
          if (Math.abs(Geom.shoelace(band(lo, mid))) < whole * i / n) c = mid; else e = mid;
        }
        cuts.push((c + e) / 2);
      }
    }
    const edge = [lo, ...cuts, hi];
    return edge.slice(0, -1).map((t, i) => {
      const poly = band(t, edge[i + 1]);
      return { poly, build: Geom.inscribe(poly, ang).box };
    });
  },

  // How wide a piece's opening onto the road is: the length of its boundary
  // lying on the road's inner edge. A piece with none is reached only by
  // crossing something else, so that something else cannot be private land.
  entrance(poly, F, E) {
    const [u, d] = Geom.unit(F, E);
    let tot = 0;
    for (let i = 0; i < poly.length; i++) {
      const [a, b] = [poly[i], poly[(i + 1) % poly.length]];
      const off = q => Math.abs(-u[1] * (q[0] - F[0]) + u[0] * (q[1] - F[1]));
      if (Math.max(off(a), off(b)) > 0.02) continue;
      const t = [a, b].map(q => (q[0] - F[0]) * u[0] + (q[1] - F[1]) * u[1]).sort((x, y) => x - y);
      tot += Math.max(0, Math.min(t[1], d) - Math.max(t[0], 0));
    }
    return tot;
  },

  // Where two segments cross, or null if they only would if extended.
  segMeet(a, b, c, d) {
    const r = Geom.sub(b, a), sv = Geom.sub(d, c);
    const den = r[0] * sv[1] - r[1] * sv[0];
    if (Math.abs(den) < 1e-12) return null;
    const q = Geom.sub(c, a);
    const t = (q[0] * sv[1] - q[1] * sv[0]) / den;
    const u = (q[0] * r[1] - q[1] * r[0]) / den;
    return t < 0 || t > 1 || u < 0 || u > 1 ? null
         : [a[0] + r[0] * t, a[1] + r[1] * t];
  },

  // the point `d` along p->q from p
  along(p, q, d) {
    const [u] = Geom.unit(p, q);
    return [p[0] + u[0] * d, p[1] + u[1] * d];
  },

  perp(p, q) {
    const [u] = Geom.unit(p, q);
    return [-u[1], u[0]];
  },

  corners(poly) {
    return poly.map((q, i) => {
      const p = poly[(i - 1 + poly.length) % poly.length], r = poly[(i + 1) % poly.length];
      const [v1] = Geom.unit(q, p), [v2] = Geom.unit(q, r);
      return Math.acos(Math.max(-1, Math.min(1, Geom.dot(v1, v2)))) * 180 / Math.PI;
    });
  },

  // Arithmetic anyone can re-add: split the shape into triangles from its first
  // corner and give each one its own base and height.
  fanWhy(poly) {
    const parts = [];
    for (let i = 1; i < poly.length - 1; i++) {
      const b = Geom.dist(poly[0], poly[i]);
      const h = 2 * Math.abs(Geom.shoelace([poly[0], poly[i], poly[i + 1]])) / b;
      parts.push(`½ × ${b.toFixed(2)} × ${h.toFixed(2)}`);
    }
    return parts.join(" + ");
  },

  construct(corners, roadW, lots = 1, turn = 0, fan = false, equalise = "land", head = 0) {
    const [A, B, C, D] = corners;
    const P = Geom.foot(D, A, B);
    const Q = Geom.crossTo(B, A, B, D, C);
    const hW = Geom.dist(P, D), hE = Geom.dist(B, Q);
    const [u, base] = Geom.unit(P, B);
    let n = [-u[1], u[0]];
    if (Geom.dot(n, Geom.sub(D, P)) < 0) n = [-n[0], -n[1]];
    const slant = Math.atan2(hW - hE, base);
    const at = (t, h) => Geom.add(P, Geom.add(Geom.mul(u, t), Geom.mul(n, h)));
    const height = x => hW - (hW - hE) * x / base;
    const drop = roadW / Math.cos(slant);
    const inner = x => height(x) - drop;

    // where the road's inner edge cuts the two side boundaries
    const i0 = at(-400, inner(-400)), i1 = at(400, inner(400));
    const F = Geom.meet(i0, i1, A, D), E = Geom.meet(i0, i1, B, C);
    const xW = Geom.dot(Geom.sub(F, P), u);
    const depth = inner(base), width = base - xW;
    const t1h = inner(xW) - depth;
    const footW = Geom.dist(A, at(xW, 0));

    const rect = [at(xW, 0), at(base, 0), at(base, depth), at(xW, depth)];
    // A 20 ft road is the width worth having; show where its inner edge would
    // run whatever the current road is, and where it would cross the rectangle's
    // top edge -- east of that crossing a 20 ft road would not fit.
    const drop20 = 20 / Math.cos(slant);
    const inner20 = x => height(x) - drop20;
    const t3foot = Geom.foot(E, B, at(base, depth));   // E onto the rectangle's east edge
    const t3h = Geom.dist(E, t3foot);
    // The land the road leaves is the convex quad A-B-E-F. Squared to the south
    // boundary the block is the rectangle above; turned, it is the largest
    // rectangle at that angle inside the same quad, and the leftovers are what
    // the quad has outside it.
    // A dead-end road needs somewhere to turn a car round. The head is a right
    // triangle at E: one leg back along the road, then square down to the east
    // boundary. It is common ground, so it comes out before any lot is cut.
    const headW = head > 0 ? Geom.along(E, F, head) : null;
    const headV = headW ? Geom.meet(headW, Geom.add(headW, Geom.perp(E, F)), B, E) : null;
    const headPoly = headW ? [headW, E, headV] : null;
    // the same 90 deg ray carried the other way, across the road to the north
    // boundary. DC runs parallel to the road's inner edge, so MY is the road
    // width and the wedge beyond the ray, L-Y-C, is a right triangle at Y.
    const headY = headW ? Geom.meet(headW, Geom.add(headW, Geom.perp(E, F)), D, C) : null;
    const region = headW ? [A, B, headV, headW, F] : [A, B, E, F];
    // reserving the head changes what rectangle fits, so re-inscribe it
    const block = turn || headW ? Geom.inscribe(region, turn).box : rect;
    const [b0, b1, b2, b3] = block;
    const lotW = Geom.dist(b0, b1) / lots, blockD = Geom.dist(b1, b2);
    const cut = (p, q, f) => [p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f];
    // Four-sided lots tile the quad exactly, so nothing is left over at all.
    // The corner lot pays for that in shape rather than in area.
    const lotPolys = fan
      ? Geom.bands(region, F, headW || E, lots, equalise)
      : Array.from({ length: lots }, (_, i) => ({
          poly: [cut(b0, b1, i / lots), cut(b0, b1, (i + 1) / lots),
                 cut(b3, b2, (i + 1) / lots), cut(b3, b2, i / lots)], build: null }));
    const lotPieces = lotPolys.map(({ poly, build }, i) => {
      // An architect prices the rectangle he can set a house out on, not the
      // land, so a four-sided lot carries its largest inscribed rectangle too.
      const bw = build && Geom.dist(build[0], build[1]);
      const bh = build && Geom.dist(build[1], build[2]);
      return { key: lots > 1 ? `lot${i + 1}` : "rect",
               nk: lots > 1 ? "lot" : "Rectangle", ni: i + 1, poly, build,
               buildArea: build ? bw * bh : null,
               why: fan ? `${Geom.fanWhy(poly)}` : `${lotW.toFixed(2)} × ${blockD.toFixed(2)}`,
               buildWhy: build ? `${bw.toFixed(2)} × ${bh.toFixed(2)}` : null,
               area: fan ? Math.abs(Geom.shoelace(poly)) : lotW * blockD };
    });
    const roadPiece = { key: "road", nk: "Road", poly: [F, E, C, D],
      why: `(${Geom.dist(D, C).toFixed(2)} + ${Geom.dist(F, E).toFixed(2)})/2 × ${roadW.toFixed(2)} ⟂`,
      area: (Geom.dist(D, C) + Geom.dist(F, E)) / 2 * roadW,
      // past the ray the road reaches no lot, only the dead end
      beyond: headY ? { poly: [headW, headY, C, E],
                        area: Math.abs(Geom.shoelace([headW, headY, C, E])) } : null };
    const squared = [
      { key: "t1", nk: "T1 under the road", poly: [at(xW, depth), at(base, depth), F],
        why: `½ × ${width.toFixed(2)} × ${t1h.toFixed(2)}`, area: width * t1h / 2 },
      { key: "t2", nk: "T2 west corner", poly: [A, at(xW, 0), F],
        why: `½ × ${footW.toFixed(2)} × ${inner(xW).toFixed(2)}`, area: footW * inner(xW) / 2 },
      { key: "t3", nk: "T3 east corner", poly: [B, E, at(base, depth)],
        why: `½ × ${Geom.dist(B, at(base, depth)).toFixed(2)} × ${t3h.toFixed(2)}`,
        area: Geom.dist(B, at(base, depth)) * t3h / 2 },
    ];
    const pieces = [roadPiece, ...lotPieces,
                    ...(fan ? [] : turn || headW ? Geom.offcuts(region, block) : squared),
                    ...(headPoly ? [{ key: "head", nk: "TurningHead", poly: headPoly,
                        why: `½ × ${head.toFixed(2)} × ${Geom.dist(headW, headV).toFixed(2)}`,
                        area: head * Geom.dist(headW, headV) / 2 }] : [])];
    // Every vertex gets a letter; A-D are the plot corners and F, E the feet of
    // the road's inner edge, so a length can be quoted as the pair it spans.
    const vkey = q => q.map(v => v.toFixed(2)).join();
    const reg = new Map([[vkey(A), "A"], [vkey(B), "B"], [vkey(C), "C"], [vkey(D), "D"],
                         [vkey(F), "F"], [vkey(E), "E"]]);
    const spare = [..."GHJKNPQRSTUVWXZ"];   // L, M, Y name the turning head
    if (headW) {
      reg.set(vkey(headW), "M");            // back along the road from E
      reg.set(vkey(headV), "L");            // square down onto the east boundary
      reg.set(vkey(headY), "Y");            // and on across the road to DC
    }
    for (const p of pieces)
      for (const q of p.poly)
        if (!reg.has(vkey(q))) reg.set(vkey(q), spare.shift() || "?");
    // The 20 ft crossing is a point worth naming, so it gets the next letter and
    // reads like every other length: JK, KH. It is where the latent 20 ft edge
    // crosses the top of the built land -- which is the rectangle's top edge
    // squared, and the turned block's top edge turned, so take it from the
    // block rather than assuming the squared construction.
    const w20a = at(-400, inner20(-400)), w20b = at(base + 400, inner20(base + 400));
    const hitPt = fan ? null : Geom.segMeet(w20a, w20b, block[3], block[2]);
    if (hitPt && !reg.has(vkey(hitPt))) reg.set(vkey(hitPt), spare.shift() || "?");
    const nameOf = q => reg.get(vkey(q)) || "";
    for (const p of pieces) {
      // the road and the head are the common ground itself, so neither needs
      // to be told it has an entrance onto the road
      p.entrance = p.key === "road" || p.key === "head"
                 ? 0 : Geom.entrance(p.poly, F, headW || E);
      if (p.beyond)
        p.beyond.spans = p.beyond.poly.map(q => nameOf(q)).join("");
      p.name = p.nk === "lot" ? T("lot", p.ni)
             : p.nk === "offcut" ? T("offcut", p.ni) : T(p.nk);
      p.sides = p.poly.map((q, i) => Geom.dist(q, p.poly[(i + 1) % p.poly.length]));
      p.spans = p.poly.map((q, i) => nameOf(q) + nameOf(p.poly[(i + 1) % p.poly.length]));
    }
    const plot = Geom.shoelace(corners);
    return { A, B, C, D, P, Q, F, E, at, height, inner, base, xW, width, depth,
             hW, hE, slant: slant * 180 / Math.PI, roadW, rect: block, turn, fan, equalise,
             head, headPoly, headY,
             wedge: headY ? Math.abs(Geom.shoelace([headV, headY, C])) : 0,
             region, lots, lotW, blockD,
             pieces, plot, nameOf,
             allVertices: [...reg.keys()].map(kk => kk.split(",").map(Number)),
             angles: [A, B, C, D].map((_, i) => {
               const q2 = [A, B, C, D];
               const [w1] = Geom.unit(q2[i], q2[(i + 3) % 4]);
               const [w2] = Geom.unit(q2[i], q2[(i + 1) % 4]);
               return Math.acos(Geom.dot(w1, w2)) * 180 / Math.PI;
             }),
             G: at(xW, 0), H: at(base, depth), J: at(xW, depth),
             t3foot, t3h, t1h,
             top: [block[3], block[2]],
             w20: { a: w20a, b: w20b, hit: hitPt,
                    run: hitPt ? Geom.dist(block[3], hitPt) : 0 },
             dAngle: (() => {
               const [u1] = Geom.unit(D, A), [u2] = Geom.unit(D, C);
               return Math.acos(Geom.dot(u1, u2)) * 180 / Math.PI;
             })(),
             total: pieces.reduce((s, p) => s + p.area, 0) };
  },
};

// ---------------------------------------------------------------- units
const FT2 = 1 / (0.3048 * 0.3048), CENT = 435.6;
const fmt = {
  ft2: a => a.toLocaleString(undefined, { maximumFractionDigits: 0 }),
  cents: a => (a / CENT).toFixed(2),
  m2: a => (a / FT2).toFixed(1),
  len: (x, m) => m ? (x * 0.3048).toFixed(2) : x.toFixed(2),
};

// ---------------------------------------------------------------- Render
const Render = {
  fills: { road: ["#e9e9e9", "#9e9e9e"], head: ["#dcdcdc", "#616161"],
           rect: ["#d8f3f8", "#00b8d4"],
           t1: ["#fdf0d5", "#c98a1e"], t2: ["#f6dcdc", "#8b2f2f"], t3: ["#f6dcdc", "#8b2f2f"] },

  // lot1..lotN are slices of the block and carry its colour; an offcut is
  // waste, and must not read as sellable land
  fill(key) {
    return Render.fills[key] || (key.startsWith("off") ? Render.fills.t2 : Render.fills.rect);
  },

  project(m, box, padX = 96, padY = 44) {
    const all = [m.A, m.B, m.C, m.D];
    const xs = all.map(p => p[0]), ys = all.map(p => p[1]);
    const [x0, y0] = [Math.min(...xs), Math.min(...ys)];
    const [wf, hf] = [Math.max(...xs) - x0, Math.max(...ys) - y0];
    const k0 = Math.min((box.w - 2 * padX) / wf, (box.h - 2 * padY) / hf);
    const ox = (box.w - wf * k0) / 2, oy = (box.h - hf * k0) / 2;  // centred both ways
    const { z, t } = UI.view;
    return { k: k0 * z,
             X: p => [(ox + (p[0] - x0) * k0) * z + t[0],
                      (box.h - oy - (p[1] - y0) * k0) * z + t[1]] };
  },

  // One placer for both views: a rotated label is as long as its text, so each is
  // modelled as three points along its own baseline and kept clear of the rest.
  // Anything with nowhere left to sit goes out to the margin on an arrow.
  placeLabels(out, items, X, ctr, px0, px1, seed = [], bw = Infinity) {
    const placed = seed.slice(), gutter = [];
    out.push(`<defs><marker id="ar" viewBox="0 0 8 8" refX="7" refY="4"
      markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M0,1 L7,4 L0,7 z" fill="#888"/></marker></defs>`);
    let n0 = 0;
    for (const { a, b, label } of items) {
      const id = `s${n0++}`;
      const [pa, pb] = [X(a), X(b)];
      const len = Math.hypot(pb[0] - pa[0], pb[1] - pa[1]);
      if (len < 14) continue;                         // shorter than its own badge
      const cm = [(pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2];
      let n = [-(pb[1] - pa[1]) / len, (pb[0] - pa[0]) / len];
      if (n[0] * (ctr[0] - pa[0]) + n[1] * (ctr[1] - pa[1]) < 0) n = [-n[0], -n[1]];
      let ang = Math.atan2(pb[1] - pa[1], pb[0] - pa[0]) * 180 / Math.PI;
      if (ang > 90 || ang < -90) ang += 180;
      const half = label.length * 3.0;
      const u = [(pb[0] - pa[0]) / len, (pb[1] - pa[1]) / len];
      // a label is a segment along its own baseline, not a point
      const spread = c => [[c[0] - u[0] * half, c[1] - u[1] * half],
                           [c[0] + u[0] * half, c[1] + u[1] * half]];
      // A leader ties a label back to its segment, so it is free to move much
      // further than it could when its position alone had to identify it.
      let mid = null, foot = null, off = 0;
      outer:
      for (const dd of half * 2 > len ? [] : [9, 16, 24, 34, 46, 60, -12, -22, -34, -48])
        for (const f of [0.5, 0.34, 0.66, 0.2, 0.8, 0.42, 0.58, 0.1, 0.9]) {
          const on = [pa[0] + (pb[0] - pa[0]) * f, pa[1] + (pb[1] - pa[1]) * f];
          const c = [on[0] + n[0] * dd, on[1] + n[1] * dd];
          const box = spread(c);
          if (!placed.some(q => Geom.segDist(box, q) < 7 + (q[2] ?? 7))) {
            mid = c; foot = on; off = Math.abs(dd); break outer;
          }
        }
      const lead = (from, to) =>
        out.push(`<line x1="${from[0]}" y1="${from[1]}" x2="${to[0]}" y2="${to[1]}"
                   class="leader" data-seg="${id}" marker-end="url(#ar)"/>`);
      out.push(`<line x1="${pa[0]}" y1="${pa[1]}" x2="${pb[0]}" y2="${pb[1]}"
                 class="hit" data-seg="${id}"/>`);
      if (mid) {
        placed.push([...spread(mid), 7]);
        // Point at the nearest bit of the segment, not its midpoint, and only
        // once the label has actually left the line. A label slid along its own
        // segment is already sitting on it, and an arrow from there to the
        // midpoint just draws a line across the middle of the drawing.
        if (off > 15) lead(mid, foot);
        out.push(`<text x="${mid[0]}" y="${mid[1] + 4}" class="side" data-seg="${id}"
                   transform="rotate(${ang} ${mid[0]} ${mid[1]})">${label}</text>`);
        continue;
      }
      const left = cm[0] < ctr[0];
      const gx = left ? Math.max(66, px0 - 22) : Math.min(bw - 66, px1 + 22);
      let gy = cm[1];
      while (gutter.some(g => g[0] === left && Math.abs(g[1] - gy) < 15)) gy += 15;
      gutter.push([left, gy]);
      placed.push([[gx - label.length * 3, gy], [gx + label.length * 3, gy], 7]);
      lead([gx + (left ? 4 : -4), gy - 3], cm);
      // a class, not the text-anchor attribute: the stylesheet's `text` rule
      // would otherwise win and centre the label back over the drawing
      out.push(`<text x="${gx}" y="${gy}" class="side ${left ? "a-end" : "a-start"}"
                 data-seg="${id}">${label}</text>`);
    }
    return placed;
  },

  plan(m, box, metric, legend = false) {
    const all = [m.A, m.B, m.C, m.D];
    // On paper the measurements go to a legend, so the drawing needs no room
    // around it for labels and can be set out at a larger scale.
    const { k, X } = Render.project(m, box, ...(legend ? Render.pad : []));
    Render.k = k;
    Render.legend = [];
    const path = pts => "M " + pts.map(p => X(p).join(",")).join(" L ") + " Z";
    const L = x => fmt.len(x, metric);
    const out = [];

    for (const p of m.pieces) {
      const [f, s] = Render.fill(p.key);
      out.push(`<path class="piece" data-key="${p.key}" d="${path(p.poly)}"
                 fill="${f}" stroke="${s}" stroke-width="1.5"/>`);
    }
    if (m.headY) {
      const [a2, b2] = [X(m.headPoly[0]), X(m.headY)];
      out.push(`<line x1="${a2[0]}" y1="${a2[1]}" x2="${b2[0]}" y2="${b2[1]}" class="ray"/>`);
      out.push(`<path class="wedge" d="${path([m.headPoly[2], m.headY, m.C])}"/>`);
    }
    for (const p of m.pieces)
      if (p.build)
        out.push(`<path class="build" data-key="${p.key}" d="${path(p.build)}"/>`);
    out.push(`<path d="${path([m.A, m.B, m.C, m.D])}" fill="none" stroke="#000" stroke-width="2.5"/>`);
    // where a 20 ft road's inner edge would run, whatever the road is set to
    out.push(`<clipPath id="plot"><path d="${path([m.A, m.B, m.C, m.D])}"/></clipPath>`);
    const [w20a, w20b] = [X(m.w20.a), X(m.w20.b)];
    out.push(`<line x1="${w20a[0]}" y1="${w20a[1]}" x2="${w20b[0]}" y2="${w20b[1]}"
               class="w20" clip-path="url(#plot)"/>`);
    // the two red edges belong to the squared construction. Once the block is
    // turned, cut into four-sided lots or shortened by a head, they mark
    // nothing, and next to the buildable rectangles they only mislead.
    if (!m.fan && !m.turn && !m.head)
      for (const [a, b] of [[m.at(m.xW, 0), m.F], [m.B, m.at(m.base, m.depth)]]) {
        const [p, q] = [X(a), X(b)];
        out.push(`<line x1="${p[0]}" y1="${p[1]}" x2="${q[0]}" y2="${q[1]}"
                   stroke="#a00" stroke-width="2"/>`);
      }
    const fixed = [];                       // piece names, which are drawn already
    for (const p of m.pieces) {
      const c = p.poly.reduce((a, q) => [a[0] + q[0] / p.poly.length, a[1] + q[1] / p.poly.length], [0, 0]);
      const [cx, cy] = X(c);
      const big = Geom.shoelace(p.poly) * k * k > 30000;
      // Wide pieces carry their name and arithmetic. A sliver carries its tag
      // alone, turned to run along its own longest edge so it stays inside the
      // shape instead of lying across the drawing.
      let ang = 0, w2 = p.name.length * 5.4;
      if (!big) {
        w2 = p.key.length * 4.4;        // the tag is the key, not the full name
        let best = null;
        for (let i = 0; i < p.poly.length; i++) {
          const a = X(p.poly[i]), b = X(p.poly[(i + 1) % p.poly.length]);
          const d = Math.hypot(b[0] - a[0], b[1] - a[1]);
          if (!best || d > best[0]) best = [d, a, b];
        }
        ang = Math.atan2(best[2][1] - best[1][1], best[2][0] - best[1][0]) * 180 / Math.PI;
        if (ang > 90 || ang < -90) ang += 180;
      }
      // Seed along the caption's own baseline: a rotated tag does not occupy
      // the horizontal bar a rotation-blind seed would reserve for it. The rows
      // straddle the glyphs, which rise above the baseline they are drawn on.
      const ca = ang * Math.PI / 180, cu = [Math.cos(ca), Math.sin(ca)];
      fixed.push([[cx - cu[0] * w2, cy - 7 - cu[1] * w2],
                  [cx + cu[0] * w2, cy - 7 + cu[1] * w2], big ? 11 : 9]);
      out.push(big
        ? `<text x="${cx}" y="${cy}" class="lab big" data-key="${p.key}">${p.name}</text>`
        : `<text x="${cx}" y="${cy}" class="lab tagonly" data-key="${p.key}"
             transform="rotate(${ang} ${cx} ${cy})">${p.key.toUpperCase()}</text>`);
    }
    // Each piece's own side lengths, on the edges. Pieces share edges -- the
    // rectangle's top is also T1's base -- so each edge is labelled once,
    // keyed on its midpoint.
    const seen = new Map(), verts = new Map(), placed = [];
    for (const p of m.pieces) {
      const c = p.poly.reduce((s2, q) => [s2[0] + q[0] / p.poly.length,
                                          s2[1] + q[1] / p.poly.length], [0, 0]);
      for (let i = 0; i < p.poly.length; i++) {
        const a = p.poly[i], b = p.poly[(i + 1) % p.poly.length];
        verts.set(a.map(v => v.toFixed(2)).join(), a);
        if (Geom.dist(a, b) < 0.05) continue;      // float noise, not an edge
        const key = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2].map(v => Math.round(v)).join();
        if (!seen.has(key)) seen.set(key, [a, b, c, p.key]);
      }
    }
    const ctr = X(all.reduce((a, q) => [a[0] + q[0] / 4, a[1] + q[1] / 4], [0, 0]));
    const spanTxt = (a2, b2) =>
      `${m.nameOf(a2)}${m.nameOf(b2)} = ${L(Geom.dist(a2, b2))}`;

    // Segment lengths sit on their own segment, quoted as the pair they span.
    // Near-parallel edges would land their midpoints together, so a label slides
    // along its edge to the first free spot.
    const bx = [m.A, m.B, m.C, m.D].map(X);
    const px0 = Math.min(...bx.map(q => q[0])), px1 = Math.max(...bx.map(q => q[0]));
    const items = [...seen.values()].map(([a2, b2]) =>
      ({ a: a2, b: b2, label: spanTxt(a2, b2) }));
    if (m.w20.hit)
      items.push({ a: m.top[0], b: m.w20.hit, label: spanTxt(m.top[0], m.w20.hit) },
                 { a: m.w20.hit, b: m.top[1], label: spanTxt(m.w20.hit, m.top[1]) });
    if (m.headY)
      items.push({ a: m.headPoly[0], b: m.headY, label: spanTxt(m.headPoly[0], m.headY) },
                 { a: m.headY, b: m.C, label: spanTxt(m.headY, m.C) },
                 { a: m.headPoly[2], b: m.headY, label: spanTxt(m.headPoly[2], m.headY) });
    if (legend) Render.legend.push(...items.map(i => i.label));
    else Render.placeLabels(out, items, X, ctr, px0, px1,
      [...fixed, ...[...verts.values()].map(v => [X(v), X(v), 10])], box.w);

    // the four recorded boundaries, outside the plot
    const single = ([a2, b2]) => [...seen.values()].some(([u, v]) =>
      (Geom.dist(u, a2) < 0.05 && Geom.dist(v, b2) < 0.05) ||
      (Geom.dist(u, b2) < 0.05 && Geom.dist(v, a2) < 0.05));
    for (const [a2, b2] of [[m.D, m.C], [m.A, m.B], [m.B, m.C], [m.A, m.D]]) {
      if (single([a2, b2])) continue;          // already labelled on the segment
      if (legend) { Render.legend.push(spanTxt(a2, b2)); continue; }
      const [pa, pb] = [X(a2), X(b2)];
      let ang = Math.atan2(pb[1] - pa[1], pb[0] - pa[0]) * 180 / Math.PI;
      if (ang > 90 || ang < -90) ang += 180;
      let [mx, my] = [(pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2];
      const away = [mx - ctr[0], my - ctr[1]], d = Math.hypot(...away) || 1;
      mx += away[0] / d * 20; my += away[1] / d * 20;
      out.push(`<text x="${mx}" y="${my}" class="dim"
                 transform="rotate(${ang} ${mx} ${my})">${spanTxt(a2, b2)}</text>`);
    }

    if (legend && Render.mmpp) {
      const len = 100 / Render.mmpp;                 // 100 mm on paper, in px
      const [x0, y0] = [30, box.h - 16];
      out.push(`<line x1="${x0}" y1="${y0}" x2="${x0 + len}" y2="${y0}" class="sbar"/>`);
      for (let i = 0; i <= 4; i++)
        out.push(`<line x1="${x0 + len * i / 4}" y1="${y0 - 4}"
                   x2="${x0 + len * i / 4}" y2="${y0 + 4}" class="sbar"/>`);
      // above the bar, not after it: the bar is 100 mm long and the caption is
      // longer than whatever is left of the sheet beside it
      out.push(`<text x="${x0}" y="${y0 - 9}" class="sbartxt">${
        T("scaleBar", (100 * Render.scale / 1000).toFixed(1), Render.scale)}</text>`);
    }

    // a badge on every vertex, the 20 ft crossing included
    if (m.w20.hit) verts.set("w20", m.w20.hit);
    if (m.headY) verts.set("headY", m.headY);
    for (const v of verts.values()) {
      const [x, y] = X(v), nm = m.nameOf(v);
      const kind = "ABCD".includes(nm) ? "corner"
                 : "FE".includes(nm) ? "node"
                 : m.w20.hit && Geom.dist(v, m.w20.hit) < 1e-6 ? "w20"
                 : "inner";
      out.push(`<circle cx="${x}" cy="${y}" r="${kind === "corner" ? 8 : 6.5}"
                 class="badge b-${kind}"/>`);
      out.push(`<text x="${x}" y="${y + 3.5}"
                 class="${kind === "w20" ? "w20txt" : kind}">${nm}</text>`);
    }
    return out.join("\n");
  },

  // What the turn buys, in the same units as the schedule under it.
  turnNote(m, metric) {
    const hd = m.headPoly && m.pieces.find(p => p.key === "head");
    const headSays = hd ? `<p class="note">${T("headNote", fmt.len(m.head, metric),
      fmt.len(Geom.dist(m.headPoly[0], m.headPoly[2]), metric),
      fmt.ft2(hd.area), fmt.cents(hd.area))}</p>
      <p class="note">${T("wedgeNote", fmt.len(Geom.dist(m.headY, m.C), metric),
        fmt.len(Geom.dist(m.headPoly[2], m.headY), metric),
        fmt.ft2(m.wedge), fmt.cents(m.wedge))}</p>` : "";
    if (m.fan) {
      const flat = Geom.construct([m.A, m.B, m.C, m.D], m.roadW, m.lots, 0, false);
      const each = m.pieces.filter(p => p.key === "rect" || p.key.startsWith("lot"));
      const was = flat.pieces.filter(p => p.key === "rect" || p.key.startsWith("lot"));
      const gain = Math.round(each[0].area - was[0].area);
      const sharp = Math.min(...m.pieces.filter(p => p.key.startsWith("lot") || p.key === "rect")
        .flatMap(p => Geom.corners(p.poly)));
      const b = Math.min(...each.map(q => q.buildArea));
      const head = m.equalise === "buildable"
        ? T("eqNote", fmt.ft2(b), fmt.cents(b))
        : T("fanNote", fmt.ft2(each[0].area), fmt.cents(each[0].area), gain.toLocaleString());
      return headSays + `<p class="note">${head} ${T("fanCorner", sharp.toFixed(0))}</p>`;
    }
    if (!m.turn) return headSays;
    const flat = Geom.construct([m.A, m.B, m.C, m.D], m.roadW, m.lots, 0);
    const block = p => p.pieces.filter(q => q.key === "rect" || q.key.startsWith("lot"))
                        .reduce((t, q) => t + q.area, 0);
    const gain = Math.round(block(m) - block(flat));
    return headSays + `<p class="note">${T("turnNote", m.turn.toFixed(2),
      T("turnGain", gain, (gain / 435.6).toFixed(2)))}</p>`;
  },

  schedule(m, metric, cols = 1) {
    const u = metric ? "m²" : "ft²";
    const val = a => metric ? fmt.m2(a) : fmt.ft2(a);
    const L = x => fmt.len(x, metric);
    const rows = m.pieces.map(p => `<tr data-key="${p.key}">
        <td><span class="sw" style="background:${Render.fill(p.key)[0]};
            border-color:${Render.fill(p.key)[1]}"></span>${p.name}</td>
        <td class="why">${p.spans.map((sp, i) => `${sp} ${L(p.sides[i])}`).join(", ")}
            <br><i>${p.why}</i>${p.beyond ? `<br><b class="bey">${T("beyondRay")}
            ${p.beyond.spans} ${fmt.ft2(p.beyond.area)} ft²
            (${fmt.cents(p.beyond.area)} ${T("thCents")})</b>` : ""}${p.build ? `<br><b class="bld">${T("buildable")}
            ${p.buildWhy} = ${fmt.ft2(p.buildArea)} ft² (${fmt.cents(p.buildArea)} ${T("thCents")})</b>` : ""}
            ${p.key === "road" || p.key === "head" ? "" : p.entrance > 0.05
              ? `<br><span class="ent">${T("entrance")} ${L(p.entrance)}</span>`
              : `<br><span class="ent bad">${T("noFront")}</span>`}</td>
        <td class="n">${val(p.area)}</td>
        <td class="n">${fmt.cents(p.area)}</td>
        <td class="n">${(p.area / m.plot * 100).toFixed(1)}%</td></tr>`);
    const ok = Math.abs(m.total - m.plot) < 0.5;
    const head = `<thead><tr><th>${T("thPiece")}</th><th>${T("thSides")}</th>
        <th class="n">${u}</th><th class="n">${T("thCents")}</th>
        <th class="n">%</th></tr></thead>`;
    const foot = `<tfoot><tr class="${ok ? "ok" : "bad"}"><td>${T("tally")}</td><td class="why">
        ${ok ? T("partsSum") : T("partsDont") + " — " + (m.total - m.plot).toFixed(1) + " ft²"}</td>
        <td class="n">${val(m.total)}</td><td class="n">${fmt.cents(m.total)}</td>
        <td class="n">100.0%</td></tr></tfoot>`;
    if (cols === 1)
      return `<table>${head}<tbody>${rows.join("")}</tbody>${foot}</table>`;
    // A sheet of its own is wider than it is full, so the pieces run down two
    // columns and the tally sits under both.
    const half = Math.ceil(rows.length / 2);
    return `<div class="two">
        <table>${head}<tbody>${rows.slice(0, half).join("")}</tbody></table>
        <table>${head}<tbody>${rows.slice(half).join("")}</tbody></table>
      </div><table class="tally">${foot}</table>`;
  },
};

// ---------------------------------------------------------------- Explain
// The construction, one move at a time. Each step names what it adds and where
// the numbers come from; nothing appears before the step that derives it.
const Explain = {
  steps(m, L) {
    const d = (a, b) => L(Geom.dist(a, b));
    const bound = [[m.A, m.B], [m.B, m.C], [m.C, m.D], [m.D, m.A]];
    const ang = ["A", "B", "C", "D"].map((_, i) => {
      const q = [m.A, m.B, m.C, m.D];
      const [u1] = Geom.unit(q[i], q[(i + 3) % 4]), [u2] = Geom.unit(q[i], q[(i + 1) % 4]);
      return Math.acos(Geom.dot(u1, u2)) * 180 / Math.PI;
    });
    const [aA, aB, aC, aD] = ang.map(x => x.toFixed(2));
    const tan = x => Math.tan(x * Math.PI / 180).toFixed(3);
    const v = { ac: d(m.A, m.C), slant: m.slant.toFixed(2), road: L(m.roadW),
                aA, aB, aC, aD,
                ab: d(m.A, m.B), ad: d(m.A, m.D), dc: d(m.D, m.C), be: d(m.B, m.E),
                ap: L(Geom.dist(m.A, m.P)), pb: L(m.base),
                fall: L(m.base * Math.tan(m.slant * Math.PI / 180)),
                gf: d(m.G, m.F), tanA: tan(ang[0]),
                diagSrc: T(SITE.diagTaped ? "diagTaped" : "diagGuessed"),
                ...(() => {                       // the halves the diagonal makes
                  const cr = (x, y, z) => (Math.acos((x * x + y * y - z * z) /
                    (2 * x * y)) * 180 / Math.PI).toFixed(2);
                  const [ab, bc, cd, da, ac] = [Geom.dist(m.A, m.B), Geom.dist(m.B, m.C),
                    Geom.dist(m.C, m.D), Geom.dist(m.D, m.A), Geom.dist(m.A, m.C)];
                  return { bac: cr(ab, ac, bc), cad: cr(ac, da, cd),
                           acb: cr(ac, bc, ab), acd: cr(ac, cd, da),
                           sum: ang.reduce((x, y) => x + y, 0).toFixed(2) };
                })(),
                df: d(m.D, m.F), ec: d(m.E, m.C), dAngle: m.dAngle.toFixed(2),
                ag: d(m.A, m.G), gb: d(m.G, m.B), bh: d(m.B, m.H),
                jh: d(m.J, m.H), jf: d(m.J, m.F), gf: d(m.G, m.F),
                t3h: L(m.t3h), total: fmt.ft2(m.plot),
                hE: L(m.hE), hW: L(m.hW),
                drop: L(m.roadW / Math.cos(m.slant * Math.PI / 180)),
                ...Object.fromEntries(["t1", "t2", "t3"].map(k =>
                  [k + "a", fmt.ft2(m.pieces.find(p => p.key === k).area)])) };
    const work = [
      [`AC must lie between ${L(SITE.range[0] * Geom.M2FT)} and ` +
       `${L(SITE.range[1] * Geom.M2FT)}, or one of the two triangles cannot close;`,
       `ours is ${v.ac}${SITE.diagTaped ? " — taped on site" :
         ", read off satellite imagery — NOT yet taped"}`,
       `the diagonal splits the plot into triangles ABC and ACD, and three sides`,
       `fix a triangle, so every angle follows from the law of cosines —`,
       `  AC² = AB² + BC² − 2·AB·BC·cos B   (Pythagoras, plus a term for the tilt)`,
       `rearranged for the angle, cos B = (AB² + BC² − AC²) / (2·AB·BC):`,
       `B = acos((AB² + BC² − AC²) / (2·AB·BC)) = ${v.aB}°`,
       `D = acos((CD² + DA² − AC²) / (2·CD·DA)) = ${v.aD}°`,
       `A = ∠BAC + ∠CAD = ${v.bac}° + ${v.cad}° = ${v.aA}°`,
       `C = ∠ACB + ∠ACD = ${v.acb}° + ${v.acd}° = ${v.aC}°`,
       `check: A + B + C + D = ${v.sum}° (must be 360°)`],
      [`slant = 180° − A − D = 180 − ${v.aA} − ${v.aD} = ${v.slant}°`],
      [`DF = road ÷ sin D = ${v.road} ÷ sin ${v.aD}° = ${v.df}`,
       `EC = road ÷ sin C = ${v.road} ÷ sin ${v.aC}° = ${v.ec}`,
       `FE = DC − road/tan C − road/tan D = ${v.dc} − 9.04 + 0.32 = ${d(m.F, m.E)}`],
      [`AP = AD · cos A = ${v.ad} × cos ${v.aA}° = ${v.ap}`,
       `AG = GF ÷ tan A = ${v.gf} ÷ ${v.tanA} = ${v.ag}`,
       `GB = AB − AG = ${v.ab} − ${v.ag} = ${v.gb}`],
      [`hW = AD · sin A = ${v.ad} × sin ${v.aA}° = ${v.hW}`,
       `PB = AB − AP = ${v.ab} − ${v.ap} = ${v.pb}`,
       `hE = hW − PB · tan slant = ${v.hW} − ${v.fall} = ${v.hE}`,
       `drop = road ÷ cos slant = ${v.road} ÷ cos ${v.slant}° = ${v.drop}`,
       `BH = hE − drop = ${v.hE} − ${v.drop} = ${v.bh}`],
      [`JF = JH · tan slant = ${v.jh} × tan ${v.slant}° = ${v.jf}`],
      [`GF = BH + JF = ${v.bh} + ${v.jf} = ${v.gf}`,
       `AG = GF ÷ tan A = ${v.gf} ÷ ${v.tanA} = ${v.ag}`],
      [`height = BE · sin(B − 90°) = ${v.be} × sin ${(+v.aB - 90).toFixed(2)}° = ${v.t3h}`],
      [],
    ];
    const shape = [
      { segs: [...bound, [m.A, m.C]], marks: [m.A, m.B, m.C, m.D], pieces: [],
        angles: [0, 1, 2, 3] },
      { segs: bound, marks: [m.A, m.B, m.C, m.D], pieces: [], angles: [0, 3] },
      { segs: [[m.D, m.F], [m.E, m.C], [m.F, m.E], [m.D, m.C]],
        marks: [m.A, m.B, m.C, m.D, m.F, m.E], pieces: ["road"], angles: [2, 3] },
      { segs: [[m.A, m.G], [m.G, m.B], [m.F, m.G]],
        marks: [m.A, m.B, m.D, m.F, m.G], pieces: ["road"], angles: [0] },
      { segs: [[m.B, m.H], [m.G, m.J], [m.H, m.J]], marks: [m.B, m.G, m.H, m.J],
        angles: [0],
        pieces: ["road", ...m.pieces.filter(p => p.key.startsWith("lot") ||
                 p.key === "rect").map(p => p.key)] },
      { segs: [[m.J, m.H], [m.J, m.F]], marks: [m.F, m.H, m.J],
        pieces: ["road", "t1", ...m.pieces.filter(p => p.key.startsWith("lot") ||
                 p.key === "rect").map(p => p.key)] },
      { segs: [[m.A, m.G], [m.G, m.F]], marks: [m.A, m.F, m.G], angles: [0],
        pieces: ["road", "t1", "t2", ...m.pieces.filter(p => p.key.startsWith("lot") ||
                 p.key === "rect").map(p => p.key)] },
      { segs: [[m.B, m.H], [m.E, m.t3foot]], marks: [m.B, m.E, m.H], angles: [1],
        pieces: m.pieces.map(p => p.key) },
      { segs: [], marks: m.allVertices, pieces: m.pieces.map(p => p.key), table: true },
    ];
    return shape.map((sh, i) => ({ ...sh, title: T("steps")[i].t(v),
                                   body: T("steps")[i].b(v), work: work[i] }));
  },

  render(m, box, metric, step) {
    const { X } = Render.project(m, box);
    const L = x => fmt.len(x, metric);
    const out = [];
    const path = pts => "M " + pts.map(p => X(p).join(",")).join(" L ") + " Z";
    for (const p of m.pieces)
      if (step.pieces.includes(p.key)) {
        const [f, st] = Render.fill(p.key);
        out.push(`<path d="${path(p.poly)}" fill="${f}" stroke="${st}" stroke-width="1.5"/>`);
      }
    out.push(`<path d="${path([m.A, m.B, m.C, m.D])}" fill="none" stroke="#000"
               stroke-width="2.5"/>`);
    for (const [a, b] of step.segs) {
      const [pa, pb] = [X(a), X(b)];
      out.push(`<line x1="${pa[0]}" y1="${pa[1]}" x2="${pb[0]}" y2="${pb[1]}"
                 class="hilite"/>`);
    }
    // an arc at each corner the step reasons about, drawn between its two edges
    const q = [m.A, m.B, m.C, m.D];
    const seedAngles = [];
    for (const i of step.angles || []) {
      const at = X(q[i]), p1 = X(q[(i + 3) % 4]), p2 = X(q[(i + 1) % 4]);
      const un = c => { const d2 = [c[0] - at[0], c[1] - at[1]],
                              L2 = Math.hypot(...d2); return [d2[0] / L2, d2[1] / L2]; };
      const [u1, u2] = [un(p1), un(p2)];
      const r = 30, sweep = u1[0] * u2[1] - u1[1] * u2[0] > 0 ? 1 : 0;
      const [sx, sy] = [at[0] + u1[0] * r, at[1] + u1[1] * r];
      const [ex, ey] = [at[0] + u2[0] * r, at[1] + u2[1] * r];
      out.push(`<path d="M ${sx} ${sy} A ${r} ${r} 0 0 ${sweep} ${ex} ${ey}"
                 class="arc"/>`);
      const bis = [u1[0] + u2[0], u1[1] + u2[1]];
      const bl = Math.hypot(...bis) || 1;
      const lx = at[0] + bis[0] / bl * (r + 16), ly = at[1] + bis[1] / bl * (r + 16);
      seedAngles.push([[lx - 26, ly - 5], [lx + 26, ly - 5], 9]);
      out.push(`<text x="${lx}" y="${ly + 4}" class="angle">${"ABCD"[i]}
                 ${m.angles[i].toFixed(2)}°</text>`);
    }
    const bx = [m.A, m.B, m.C, m.D].map(X);
    const ctr = [bx.reduce((t, q) => t + q[0] / 4, 0), bx.reduce((t, q) => t + q[1] / 4, 0)];
    Render.placeLabels(out,
      step.segs.map(([a, b]) => ({ a, b,
        label: `${m.nameOf(a)}${m.nameOf(b)} = ${L(Geom.dist(a, b))}` })),
      X, ctr, Math.min(...bx.map(q => q[0])), Math.max(...bx.map(q => q[0])),
      [...seedAngles, ...step.marks.map(v => [X(v), X(v), 10])], box.w);

    for (const v of step.marks) {
      const nm = m.nameOf(v);
      const [x, y] = X(v);
      const kind = "ABCD".includes(nm) ? "corner" : "FE".includes(nm) ? "node" : "inner";
      out.push(`<circle cx="${x}" cy="${y}" r="8" class="badge b-${kind}"/>`);
      out.push(`<text x="${x}" y="${y + 3.5}" class="${kind}">${nm}</text>`);
    }
    return out.join("\n");
  },
};

// ---------------------------------------------------------------- self-check
// The page derives everything itself; these vectors are the Python's answers for
// the recorded sides, so the two can never quietly disagree.
function selfCheck(sides) {
  const same = ["north", "east", "south", "west", "diagonal"]
    .every(k => Math.abs(sides[k] - SITE.sides[k]) < 1e-9);
  if (!same) return T("checkEdited");
  const corners = Geom.closure(SITE.sides), bad = [];
  for (const [w, want] of Object.entries(SITE.vectors)) {
    const got = Geom.construct(corners, +w).pieces.map(p => p.area);
    want.forEach((v, i) => { if (Math.abs(v - got[i]) > 0.5) bad.push(`${w}ft/${i}`); });
  }
  return bad.length ? T("checkFail", bad.join(" "))
                    : T("checkPass", Object.keys(SITE.vectors).length);
}

// The drawing band inside an A4 landscape sheet's margins, in millimetres.
// 297 x 210 less an 8 mm margin, keeping 70 mm of the height for the legend
// and the notes under the drawing.
const PAPER = { w: 281, h: 124 };

// ---------------------------------------------------------------- UI
const UI = {
  read() {
    const v = id => +document.getElementById(id).value;
    return { north: v("north"), east: v("east"), south: v("south"), west: v("west"),
             diagonal: v("diagonal"), ends: "AC" };
  },

  draw() {
    if (UI.mode === "explain") return UI.explain();
    const $ = s => document.querySelector(s);
    const sides = UI.read(), metric = $("#metric").checked;
    const roadW = +$("#road").value, lots = +$("#lots").value;
    const turn = +$("#turn").value, fan = $("#fan").checked;
    const equalise = $("#eqbuild").checked ? "buildable" : "land";
    const head = +$("#head").value;
    $("#roadv").textContent = fmt.len(roadW, metric) + (metric ? " m" : " ft");
    $("#lotsv").textContent = lots === 1 ? T("oneRect") : T("lots", lots);
    $("#turnv").textContent = turn ? `${turn.toFixed(2)}°` : T("squareOn");
    $("#headv").textContent = head ? fmt.len(head, metric) + (metric ? " m" : " ft")
                                   : T("headOff");
    document.body.classList.toggle("fanning", fan);
    try {
      const m = Geom.construct(Geom.closure(sides), roadW, lots, turn, fan, equalise, head);
      if (!isFinite(m.total) || m.depth <= 0) throw new Error(T("noRoom"));
      const svg = $("#plan"), b = svg.getBoundingClientRect();
      const paper = document.body.classList.contains("printing");
      // Paper works the other way round from the screen. The screen fits the
      // drawing to whatever box the window leaves. Paper fixes the box, works
      // out what scale that box holds, then sets the element in millimetres so
      // the scale is real -- so the box cannot be read back off the element.
      const bx = paper ? UI.paperBox(m, svg) : { w: b.width, h: b.height };
      svg.setAttribute("viewBox", `0 0 ${bx.w} ${bx.h}`);
      svg.innerHTML = Render.plan(m, bx, metric, paper);
      if (paper) UI.setLegend();
      $("#sched").innerHTML =
        Render.turnNote(m, metric) + Render.schedule(m, metric, paper ? 2 : 1);
      UI.m = m;
      $("#slant").textContent = m.slant.toFixed(2);
      $("#area").textContent =
        `${fmt.ft2(m.plot)} ft² = ${fmt.cents(m.plot)} cents = ${fmt.m2(m.plot)} m²`;
    } catch (e) {
      $("#sched").innerHTML = `<p class="bad">${T("cannot")}: ${e.message}</p>`;
      $("#plan").innerHTML = "";
      return;
    }
    const msg = selfCheck(sides);
    $("#check").textContent = msg;
    $("#check").className = msg.startsWith("self-check passed") ? "ok"
                          : msg.startsWith("self-check FAILED") ? "bad" : "";
    UI.hover();
  },

  hover() {
    const set = (k, on) => document.querySelectorAll(`[data-key="${k}"]`)
      .forEach(e => e.classList.toggle("hi", on));
    const setSeg = (id, on) => document.querySelectorAll(`[data-seg="${id}"]`)
      .forEach(e => e.classList.toggle("hi", on));
    document.querySelectorAll("[data-seg]").forEach(e => {
      e.onmouseenter = () => setSeg(e.dataset.seg, true);
      e.onmouseleave = () => setSeg(e.dataset.seg, false);
    });
    const tip = document.querySelector("#tip");
    const show = (key, x, y) => {
      const p = (UI.m && UI.m.pieces || []).find(q => q.key === key);
      if (!p) return;
      const metric = document.querySelector("#metric").checked;
      tip.innerHTML = `<b>${p.name}</b><i>${p.why}</i>` +
        `<span>${fmt.ft2(p.area)} ft² &nbsp;·&nbsp; ${fmt.cents(p.area)} ${T("thCents")}` +
        ` &nbsp;·&nbsp; ${fmt.m2(p.area)} m²</span>` +
        `<span>${(p.area / UI.m.plot * 100).toFixed(1)}% ${T("ofPlot")}</span>`;
      tip.hidden = false;
      const b = tip.getBoundingClientRect();
      tip.style.left = Math.min(x + 14, innerWidth - b.width - 8) + "px";
      tip.style.top = Math.max(8, y - b.height - 12) + "px";
    };
    document.querySelectorAll("[data-key]").forEach(e => {
      e.onmouseenter = () => set(e.dataset.key, true);
      e.onmouseleave = () => { set(e.dataset.key, false); tip.hidden = true; };
      e.onmousemove = ev => show(e.dataset.key, ev.clientX, ev.clientY);
    });
  },

  mode: "plan",
  step: 0,
  view: { z: 1, t: [0, 0] },

  zoomAt(c, factor) {
    const v = UI.view, z2 = Math.min(12, Math.max(0.4, v.z * factor));
    v.t = [c[0] - (c[0] - v.t[0]) * (z2 / v.z), c[1] - (c[1] - v.t[1]) * (z2 / v.z)];
    v.z = z2;
    UI.draw();
  },

  fit() { UI.view = { z: 1, t: [0, 0] }; UI.draw(); },

  wirePanZoom() {
    const svg = document.querySelector("#plan");
    svg.addEventListener("wheel", e => {
      e.preventDefault();
      const b = svg.getBoundingClientRect();
      UI.zoomAt([e.clientX - b.left, e.clientY - b.top], Math.exp(-e.deltaY * 0.0015));
    }, { passive: false });
    const live = new Map();
    let from = null, pinch = null;
    const gap = () => {
      const [p, q] = [...live.values()];
      return { d: Math.hypot(q[0] - p[0], q[1] - p[1]),
               mid: [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2] };
    };
    svg.addEventListener("pointerdown", e => {
      live.set(e.pointerId, [e.clientX, e.clientY]);
      // capture keeps a drag alive past the edge of the svg; not being able to
      // take it is not a reason to drop the gesture
      try { svg.setPointerCapture(e.pointerId); } catch (err) { /* no live pointer */ }
      if (live.size === 2) { pinch = gap(); from = null; }
      else { from = [e.clientX, e.clientY]; svg.classList.add("grabbing"); }
    });
    svg.addEventListener("pointermove", e => {
      if (!live.has(e.pointerId)) return;
      live.set(e.pointerId, [e.clientX, e.clientY]);
      if (live.size === 2 && pinch) {
        const now = gap(), b = svg.getBoundingClientRect();
        UI.zoomAt([now.mid[0] - b.left, now.mid[1] - b.top], now.d / pinch.d);
        pinch = now;
        return;
      }
      if (!from) return;
      UI.view.t = [UI.view.t[0] + e.clientX - from[0], UI.view.t[1] + e.clientY - from[1]];
      from = [e.clientX, e.clientY];
      UI.draw();
    });
    for (const ev of ["pointerup", "pointercancel", "pointerleave"])
      svg.addEventListener(ev, e => {
        live.delete(e.pointerId);
        if (live.size < 2) pinch = null;
        from = null; svg.classList.remove("grabbing");
      });
    svg.addEventListener("dblclick", () => UI.fit());
    document.querySelector("#zin").onclick = () =>
      UI.zoomAt([svg.clientWidth / 2, svg.clientHeight / 2], 1.4);
    document.querySelector("#zout").onclick = () =>
      UI.zoomAt([svg.clientWidth / 2, svg.clientHeight / 2], 1 / 1.4);
    document.querySelector("#zfit").onclick = () => UI.fit();
  },

  setPanel(hidden) {
    document.body.classList.toggle("no-panel", hidden);
    document.querySelector("#panel").textContent = hidden ? "‹" : "›";
    try { localStorage.setItem("tslr-panel", hidden ? "0" : "1"); } catch (e) { /* private */ }
    UI.draw();                      // the fit is measured against the svg's box
  },

  explain() {
    if (+document.querySelector("#turn").value) {
      document.querySelector("#sched").innerHTML = `<p class="note">${T("turnExplain")}</p>`;
      return;
    }
    const $ = s2 => document.querySelector(s2);
    const sides = UI.read(), metric = $("#metric").checked;
    const m = Geom.construct(Geom.closure(sides), +$("#road").value, +$("#lots").value);
    const steps = Explain.steps(m, x => fmt.len(x, metric));
    UI.step = Math.max(0, Math.min(UI.step, steps.length - 1));
    const st = steps[UI.step];
    const svg = $("#plan"), b = svg.getBoundingClientRect();
    svg.setAttribute("viewBox", `0 0 ${b.width} ${b.height}`);
    svg.innerHTML = Explain.render(m, { w: b.width, h: b.height }, metric, st);
    $("#stepno").textContent = `${UI.step + 1} / ${steps.length}`;
    $("#steps").max = steps.length - 1;
    $("#steps").value = UI.step;
    $("#sched").innerHTML = `<h2>${st.title}</h2><p>${st.body}</p>` +
      (st.work && st.work.length
        ? `<div class="work"><b>${T("working")}</b><ul>` +
          st.work.map(w => `<li>${w}</li>`).join("") + "</ul></div>"
        : "") +
      (st.table ? Render.schedule(m, metric) : "");
    $("#area").textContent =
      `${fmt.ft2(m.plot)} ft² = ${fmt.cents(m.plot)} cents = ${fmt.m2(m.plot)} m²`;
    $("#slant").textContent = m.slant.toFixed(2);
  },

  setMode(mode) {
    UI.mode = mode;
    document.body.classList.toggle("explaining", mode === "explain");
    document.querySelector("#explain").textContent =
      mode === "explain" ? T("backBtn") : T("explainBtn");
    UI.draw();
  },

  // The seam between the drawing and the panel is draggable, so a long
  // schedule and a big drawing do not have to fight over one fixed split.
  // A drawing is only worth printing if a ruler agrees with it. Pick the
  // largest standard scale whose sheet still fits A4 landscape, then size the
  // SVG in millimetres so one foot on the ground is exactly its share of one.
  // Size the sheet from the plot, not the other way round. A fixed box wastes
  // whichever dimension the plot does not need, and that waste is what decides
  // the scale. `k` is pinned so one foot is exactly its share of a millimetre.
  paperBox(m, svg) {
    // A vertex badge is 8 px across and PX is px per foot, so 6 ft of margin
    // clears it. FOOT leaves a strip under the drawing for the check bar.
    const MAR = 6, FOOT = 10, PX = 4.2;
    const xs = [m.A, m.B, m.C, m.D].map(p => p[0]);
    const ys = [m.A, m.B, m.C, m.D].map(p => p[1]);
    const wf = Math.max(...xs) - Math.min(...xs) + 2 * MAR;
    const hf = Math.max(...ys) - Math.min(...ys) + 2 * MAR + FOOT;
    Render.scale = [50, 75, 100, 125, 150, 200, 250, 300, 400, 500, 750, 1000]
      .find(v => wf * 304.8 / v <= PAPER.w && hf * 304.8 / v <= PAPER.h)
      || Math.ceil(wf * 304.8 / PAPER.w / 100) * 100;
    Render.mmpp = 304.8 / (Render.scale * PX);
    Render.pad = [MAR * PX, MAR * PX];
    const box = { w: wf * PX, h: hf * PX };
    svg.style.width = (box.w * Render.mmpp).toFixed(2) + "mm";
    svg.style.height = (box.h * Render.mmpp).toFixed(2) + "mm";
    return box;
  },

  setLegend() {
    const leg = document.querySelector("#legend");
    if (!leg) return;
    leg.innerHTML = `<h3>${T("legendHead", Render.scale)}</h3><ul>` +
      [...new Set(Render.legend)].sort().map(t => `<li>${t}</li>`).join("") + "</ul>";
  },

  // No library: the browser already turns a page into a PDF. The drawing is
  // resized to the paper's proportions and redrawn first, so what prints is
  // laid out for the page rather than scaled off the screen.
  toPdf() {
    // the host injects a badge into the page; it is not part of the sheet
    for (const a of document.querySelectorAll('a[href*="netlify"]'))
      (a.closest("div") || a).classList.add("host-badge");
    const view = UI.view;
    UI.view = { z: 1, t: [0, 0] };                   // paper is not pan and zoom
    document.body.classList.add("printing");
    UI.draw();
    const done = () => {
      document.body.classList.remove("printing");
      const svg = document.querySelector("#plan");
      svg.style.width = svg.style.height = "";
      Render.mmpp = 0;
      UI.view = view;
      UI.draw();
    };
    window.addEventListener("afterprint", done, { once: true });
    window.print();
    setTimeout(() => {                       // some browsers never fire afterprint
      if (document.body.classList.contains("printing")) done();
    }, 1500);
  },

  wireGrip() {
    const grip = document.querySelector("#grip");
    const right = document.querySelector("#right");
    if (!grip || !right) return;
    const setH = h => {
      right.style.height =
        Math.max(60, Math.min(window.innerHeight - 160, h)) + "px";
    };
    const saved = +localStorage.getItem("tslr-panel-h");
    if (saved) setH(saved);
    let queued = false;
    grip.addEventListener("pointerdown", e => {
      grip.classList.add("drag");
      try { grip.setPointerCapture(e.pointerId); } catch (err) { /* fine */ }
      const move = ev => {
        setH(window.innerHeight - ev.clientY);
        if (queued) return;
        queued = true;                       // one redraw a frame, not one a pixel
        requestAnimationFrame(() => { queued = false; UI.draw(); });
      };
      const up = () => {
        grip.classList.remove("drag");
        localStorage.setItem("tslr-panel-h", parseInt(right.style.height, 10));
        grip.removeEventListener("pointermove", move);
        grip.removeEventListener("pointerup", up);
        UI.draw();
      };
      grip.addEventListener("pointermove", move);
      grip.addEventListener("pointerup", up);
      e.preventDefault();
    });
  },

  applyLang() {
    const set = (id, txt) => { const e = document.getElementById(id);
      if (e) e.textContent = txt; };
    document.documentElement.lang = LANG;
    set("lang", T("lang"));
    set("l-bnd", T("boundary"));
    for (const k of ["north", "east", "south", "west", "diagonal"]) set("l-" + k, T(k));
    set("l-road", T("roadLabel"));
    set("l-lots", T("splitLabel"));
    set("l-turn", T("turnLabel"));
    set("bestturn", T("bestBtn"));
    set("l-fan", T("fanLabel"));
    set("l-eqbuild", T("eqLabel"));
    set("l-head", T("headLabel"));
    set("l-metric", T("metres"));
    set("zfit", T("fit"));
    set("pdf", T("pdfBtn"));
    set("l-closure", T("closure"));
    set("l-slant", T("slants"));
    const f = document.getElementById("l-foot");
    if (f) f.textContent = `${T("footer")} ${T("registered")} ${f.dataset.reg} m².`;
    document.querySelector("#explain").textContent =
      UI.mode === "explain" ? T("backBtn") : T("explainBtn");
    UI.draw();
  },

  init() {
    UI.wireGrip();
    document.querySelector("#pdf").onclick = UI.toPdf;
    document.querySelector("#bestturn").onclick = () => {
      const m = Geom.construct(Geom.closure(UI.read()), +document.querySelector("#road").value);
      document.querySelector("#turn").value = Geom.bestTurn(m.region);
      UI.draw();
    };
    document.querySelector("#panel").onclick = () =>
      UI.setPanel(!document.body.classList.contains("no-panel"));
    addEventListener("keydown", e => {
      if (e.key === "p" && !/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName))
        UI.setPanel(!document.body.classList.contains("no-panel"));
    });
    document.querySelector("#lang").onclick = () => {
      LANG = LANG === "en" ? "ta" : "en";
      try { localStorage.setItem("tslr-lang", LANG); } catch (e) { /* private mode */ }
      UI.applyLang();
    };
    try { LANG = localStorage.getItem("tslr-lang") || "en"; } catch (e) { /* private mode */ }
    document.querySelector("#explain").onclick = () =>
      UI.setMode(UI.mode === "explain" ? "plan" : "explain");
    document.querySelector("#steps").addEventListener("input", e => {
      UI.step = +e.target.value; UI.explain();
    });
    document.querySelector("#prev").onclick = () => { UI.step--; UI.explain(); };
    document.querySelector("#next").onclick = () => { UI.step++; UI.explain(); };
    addEventListener("keydown", e => {
      if (UI.mode !== "explain") return;
      if (e.key === "ArrowRight") { UI.step++; UI.explain(); }
      if (e.key === "ArrowLeft") { UI.step--; UI.explain(); }
    });
    for (const [k, v] of Object.entries(SITE.sides))
      if (document.getElementById(k)) document.getElementById(k).value = v;
    document.querySelectorAll("input").forEach(e => e.addEventListener("input", UI.draw));
    addEventListener("resize", UI.draw);
    UI.wirePanZoom();
    let hide = false;
    try { hide = localStorage.getItem("tslr-panel") === "0"; } catch (e) { /* private */ }
    document.body.classList.toggle("no-panel", hide);
    document.querySelector("#panel").textContent = hide ? "‹" : "›";
    UI.applyLang();
  },
};

addEventListener("DOMContentLoaded", UI.init);
