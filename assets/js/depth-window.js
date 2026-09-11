(function () {
  "use strict";

  // "Janelas de profundidade": embeddable off-axis-projection viewports.
  // Only one window is ever open at a time: opening one closes whichever
  // was open before, stops the webcam, and frees the WebGL context — so
  // reading through the post never leaves multiple cameras/renderers
  // running in the background. See the blog post that ships this file for
  // the technique (Kooima's generalized perspective projection) and the
  // privacy model (camera never leaves the browser, no frames are ever
  // uploaded or stored).

  var THREE_JS_SRC = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js";
  var MEDIAPIPE_VISION_SRC = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/vision_bundle.mjs";
  var MEDIAPIPE_WASM_BASE = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm";
  var FACE_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";

  var CM_PER_CSS_PX = 2.54 / 96; // assumes a standard 96dpi CSS reference pixel
  var ASSUMED_FOCAL_PX = 620;
  var HFOV_DEG = 60;
  var DIST_SMOOTHING = 0.25;
  var POS_SMOOTHING = 0.18;
  var FACE_LOST_TIMEOUT_MS = 600;

  var LEFT_EYE_CORNER = 33;
  var RIGHT_EYE_CORNER = 263;
  var LEFT_IRIS = 468;
  var RIGHT_IRIS = 473;

  var widgets = [];
  var currentOpen = null;
  var THREE = null;
  var faceLandmarker = null;
  var video = null;
  var enginePromise = null;
  var rafId = 0;
  var lastVideoTime = -1;
  var smoothedEyePixelDist = null;
  var eyeCm = { x: 0, y: 0, z: 55 };
  var smoothedEyeCm = { x: 0, y: 0, z: 55 };
  var lastFaceSeenAt = 0;

  function clamp(v, min, max) { return Math.min(Math.max(v, min), max); }

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var existing = document.querySelector('script[data-depth-window-vendor="' + src + '"]');
      if (existing) {
        if (existing.dataset.loaded === "true") { resolve(); return; }
        existing.addEventListener("load", function () { resolve(); });
        existing.addEventListener("error", reject);
        return;
      }
      var el = document.createElement("script");
      el.src = src;
      el.async = true;
      el.dataset.depthWindowVendor = src;
      el.addEventListener("load", function () { el.dataset.loaded = "true"; resolve(); });
      el.addEventListener("error", reject);
      document.head.appendChild(el);
    });
  }

  function loadEngine() {
    if (enginePromise) { return enginePromise; }
    enginePromise = loadScript(THREE_JS_SRC)
      .then(function () { THREE = window.THREE; })
      .then(function () { return import(/* webpackIgnore: true */ MEDIAPIPE_VISION_SRC); })
      .then(function (visionModule) {
        return visionModule.FilesetResolver.forVisionTasks(MEDIAPIPE_WASM_BASE).then(function (fileset) {
          return visionModule.FaceLandmarker.createFromOptions(fileset, {
            baseOptions: { modelAssetPath: FACE_MODEL_URL, delegate: "GPU" },
            outputFaceBlendshapes: false,
            outputFacialTransformationMatrixes: false,
            runningMode: "VIDEO",
            numFaces: 1,
            refineLandmarks: true
          });
        });
      })
      .then(function (landmarker) { faceLandmarker = landmarker; })
      .catch(function (err) { enginePromise = null; throw err; });
    return enginePromise;
  }

  function ensureCamera() {
    if (video && video.srcObject && video.srcObject.active) {
      return Promise.resolve();
    }
    return navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: "user" }, audio: false })
      .then(function (stream) {
        video = video || document.createElement("video");
        video.autoplay = true; video.playsInline = true; video.muted = true;
        video.srcObject = stream;
        return new Promise(function (resolve) { video.onloadedmetadata = resolve; }).then(function () { video.play(); });
      });
  }

  function stopCamera() {
    if (video && video.srcObject) {
      video.srcObject.getTracks().forEach(function (t) { t.stop(); });
      video.srcObject = null;
    }
    lastVideoTime = -1;
    smoothedEyePixelDist = null;
  }

  // A vertical-gradient sky, wrapped on the inside of a big sphere so it
  // always fills the frame no matter which way the head-tracked camera
  // turns — the open-air equivalent of the enclosed box: there is never a
  // void to peek into, just more sky.
  function makeSkyTexture(top, mid, bottom) {
    var w = 128, h = 512;
    var c = document.createElement("canvas");
    c.width = w; c.height = h;
    var ctx = c.getContext("2d");
    var grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, top);
    grad.addColorStop(0.55, mid);
    grad.addColorStop(1, bottom);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
    return new THREE.CanvasTexture(c);
  }

  function buildSkyDome(scene, top, mid, bottom, radius) {
    var sky = new THREE.Mesh(
      new THREE.SphereGeometry(radius || 38, 24, 16),
      new THREE.MeshBasicMaterial({ map: makeSkyTexture(top, mid, bottom), side: THREE.BackSide, fog: false, depthWrite: false })
    );
    scene.add(sky);
    return sky;
  }

  // A building facade: a base color punched with a grid of randomly lit
  // windows, so a plain box reads as an apartment block rather than a
  // flat-shaded cube.
  function makeWindowTexture(base, lit, cols, rows) {
    var w = 128, h = 256;
    var c = document.createElement("canvas");
    c.width = w; c.height = h;
    var ctx = c.getContext("2d");
    ctx.fillStyle = base;
    ctx.fillRect(0, 0, w, h);
    var colW = w / cols, rowH = h / rows;
    var pad = Math.min(colW, rowH) * 0.22;
    for (var r = 0; r < rows; r++) {
      for (var cI = 0; cI < cols; cI++) {
        if (Math.random() < 0.5) {
          ctx.fillStyle = lit;
          ctx.fillRect(cI * colW + pad, r * rowH + pad, colW - pad * 2, rowH - pad * 2);
        }
      }
    }
    var tex = new THREE.CanvasTexture(c);
    return tex;
  }

  function makeStreetTexture() {
    var w = 128, h = 256;
    var c = document.createElement("canvas");
    c.width = w; c.height = h;
    var ctx = c.getContext("2d");
    ctx.fillStyle = "#1b1e24";
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = "#d8b94a";
    ctx.lineWidth = 4;
    ctx.setLineDash([16, 16]);
    ctx.beginPath();
    ctx.moveTo(w / 2, 0);
    ctx.lineTo(w / 2, h);
    ctx.stroke();
    var tex = new THREE.CanvasTexture(c);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(1, 8);
    return tex;
  }

  function createBaseInstance(canvas) {
    var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x05070d, 1);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    if ("outputEncoding" in renderer) { renderer.outputEncoding = THREE.sRGBEncoding; }
    // Without tone mapping, a bright spotlight hitting a large flat
    // surface head-on (the photo cards especially) clips straight to
    // white instead of rolling off — ACES keeps highlights readable.
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;

    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(50, 1, 0.05, 100);

    var windowFrame = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.PlaneGeometry(1, 1)),
      new THREE.LineBasicMaterial({ color: 0x4a82f0, transparent: true, opacity: 0.4 })
    );
    scene.add(windowFrame);

    var bodyMat = new THREE.MeshStandardMaterial({ color: 0x000000, roughness: 1 });
    var bodyHead = new THREE.Mesh(new THREE.SphereGeometry(0.22, 14, 14), bodyMat);
    bodyHead.position.set(0, 0.55, 0);
    var bodyShoulders = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.65, 0.7, 14), bodyMat);
    bodyShoulders.position.set(0, -0.05, 0);
    var bodyProxy = new THREE.Group();
    bodyProxy.add(bodyHead, bodyShoulders);
    bodyProxy.traverse(function (o) {
      if (o.isMesh) { o.castShadow = true; o.receiveShadow = false; o.layers.set(1); }
    });
    bodyProxy.position.set(0, 0, 1.5);
    scene.add(bodyProxy);

    function addSun(color, targetZ, intensity) {
      var sun = new THREE.SpotLight(color, intensity || 3.2, 26, Math.PI / 6, 0.45, 1.2);
      sun.position.set(2.2, 3.2, 3.2);
      sun.target.position.set(0, -1, targetZ);
      sun.castShadow = true;
      sun.shadow.mapSize.set(1024, 1024);
      sun.shadow.camera.near = 1;
      sun.shadow.camera.far = 20;
      sun.shadow.bias = -0.0018;
      sun.shadow.camera.layers.enable(1);
      scene.add(sun, sun.target);
      return sun;
    }

    return {
      canvas: canvas, renderer: renderer, scene: scene, camera: camera,
      windowFrame: windowFrame, bodyProxy: bodyProxy, addSun: addSun,
      floaters: [], lastW: 0, lastH: 0
    };
  }

  // A closed box behind the window — floor, ceiling, both side walls and a
  // back wall, all meeting at real corners. Without this, tilting your
  // head toward a corner reveals nothing (the void keeps going forever),
  // which breaks the "looking into a real space" illusion immediately.
  // zNear is normally 0 (the box's open front is the window plane itself).
  function buildEnclosure(scene, opts) {
    var halfW = opts.halfW, halfH = opts.halfH;
    var zNear = opts.zNear, zFar = opts.zFar;
    var w = halfW * 2, h = halfH * 2, d = Math.abs(zFar - zNear);
    var midZ = (zNear + zFar) / 2;

    var floor = new THREE.Mesh(new THREE.PlaneGeometry(w, d), opts.floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(0, -halfH, midZ);
    floor.receiveShadow = true;
    scene.add(floor);

    var ceiling = new THREE.Mesh(new THREE.PlaneGeometry(w, d), opts.ceilingMat);
    ceiling.rotation.x = Math.PI / 2;
    ceiling.position.set(0, halfH, midZ);
    ceiling.receiveShadow = true;
    scene.add(ceiling);

    var left = new THREE.Mesh(new THREE.PlaneGeometry(d, h), opts.wallMat);
    left.rotation.y = Math.PI / 2;
    left.position.set(-halfW, 0, midZ);
    left.receiveShadow = true;
    scene.add(left);

    var right = new THREE.Mesh(new THREE.PlaneGeometry(d, h), opts.wallMat2 || opts.wallMat);
    right.rotation.y = -Math.PI / 2;
    right.position.set(halfW, 0, midZ);
    right.receiveShadow = true;
    scene.add(right);

    var back = new THREE.Mesh(new THREE.PlaneGeometry(w, h), opts.backMat);
    back.position.set(0, 0, zFar);
    back.receiveShadow = true;
    scene.add(back);

    return { floor: floor, ceiling: ceiling, left: left, right: right, back: back };
  }

  // Scene 1 — a bedroom, loosely after Van Gogh's "Bedroom in Arles": bed,
  // nightstand with a jug, two chairs, a small table, a window and a
  // couple of framed pictures on the back wall. A recognizable room reads
  // the off-axis distortion far better than an abstract shape ever could
  // — you can tell a corner is "wrong" or "right" because you know what a
  // corner of a room is supposed to look like.
  function buildBedroomScene(inst) {
    var scene = inst.scene;
    scene.fog = new THREE.Fog(0x1c2e33, 7, 17);
    scene.add(new THREE.HemisphereLight(0xbfe0e6, 0x2a1f18, 0.6));
    inst.addSun(0xfff2d0, -4, 2.1);

    var rim = new THREE.PointLight(0xffb066, 0.5, 20);
    rim.position.set(-2, 1.5, -3);
    scene.add(rim);

    var room = new THREE.Group();
    scene.add(room);
    var floorY = -2.4;

    buildEnclosure(room, {
      halfW: 3.4, halfH: 2.4, zNear: 0, zFar: -7,
      floorMat: new THREE.MeshStandardMaterial({ color: 0xa8602c, roughness: 0.92 }),
      ceilingMat: new THREE.MeshStandardMaterial({ color: 0xcbb98f, roughness: 0.95 }),
      wallMat: new THREE.MeshStandardMaterial({ color: 0x3f7f86, roughness: 0.9 }),
      wallMat2: new THREE.MeshStandardMaterial({ color: 0x3f7f86, roughness: 0.9 }),
      backMat: new THREE.MeshStandardMaterial({ color: 0x3f7f86, roughness: 0.9 })
    });

    // window on the back wall, glowing like daylight from outside
    var windowGlow = new THREE.Mesh(
      new THREE.PlaneGeometry(0.9, 1.1),
      new THREE.MeshBasicMaterial({ color: 0xdcefe0 })
    );
    windowGlow.position.set(1.7, 0.5, -6.96);
    room.add(windowGlow);
    var windowEdges = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.PlaneGeometry(0.9, 1.1)),
      new THREE.LineBasicMaterial({ color: 0x1c2b2f })
    );
    windowEdges.position.set(1.7, 0.5, -6.94);
    room.add(windowEdges);

    // bed: frame, mattress, blanket, pillow
    var bedFrame = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.35, 3.0), new THREE.MeshStandardMaterial({ color: 0x6b3f22, roughness: 0.85 }));
    bedFrame.position.set(-1.7, floorY + 0.18, -3.4);
    bedFrame.castShadow = true; bedFrame.receiveShadow = true;
    room.add(bedFrame);

    var mattress = new THREE.Mesh(new THREE.BoxGeometry(1.9, 0.22, 2.9), new THREE.MeshStandardMaterial({ color: 0xf2e9d8, roughness: 0.9 }));
    mattress.position.set(-1.7, bedFrame.position.y + 0.28, -3.4);
    mattress.castShadow = true; mattress.receiveShadow = true;
    room.add(mattress);

    var blanket = new THREE.Mesh(new THREE.BoxGeometry(1.9, 0.14, 1.7), new THREE.MeshStandardMaterial({ color: 0xd8455a, roughness: 0.85 }));
    blanket.position.set(-1.7, mattress.position.y + 0.17, -2.9);
    blanket.castShadow = true; blanket.receiveShadow = true;
    room.add(blanket);

    var pillow = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.2, 0.5), new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.9 }));
    pillow.position.set(-1.7, mattress.position.y + 0.2, -4.6);
    pillow.castShadow = true;
    room.add(pillow);

    // nightstand with a jug
    var nightstand = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.6, 0.5), new THREE.MeshStandardMaterial({ color: 0x8a5a34, roughness: 0.8 }));
    nightstand.position.set(-0.35, floorY + 0.3, -5.3);
    nightstand.castShadow = true; nightstand.receiveShadow = true;
    room.add(nightstand);

    var jug = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.13, 0.28, 10), new THREE.MeshStandardMaterial({ color: 0xe6e6e6, roughness: 0.4, metalness: 0.1 }));
    jug.position.set(-0.35, nightstand.position.y + 0.44, -5.3);
    jug.castShadow = true;
    room.add(jug);

    // two chairs
    function makeChair(x, z, color) {
      var group = new THREE.Group();
      var seat = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.08, 0.5), new THREE.MeshStandardMaterial({ color: color, roughness: 0.7 }));
      group.add(seat);
      var back = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.55, 0.06), new THREE.MeshStandardMaterial({ color: color, roughness: 0.7 }));
      back.position.set(0, 0.3, -0.22);
      group.add(back);
      var legGeo = new THREE.CylinderGeometry(0.03, 0.03, 0.42, 6);
      [[-0.2, -0.2], [0.2, -0.2], [-0.2, 0.2], [0.2, 0.2]].forEach(function (p) {
        var leg = new THREE.Mesh(legGeo, new THREE.MeshStandardMaterial({ color: 0x4a2f1c, roughness: 0.8 }));
        leg.position.set(p[0], -0.25, p[1]);
        group.add(leg);
      });
      group.position.set(x, floorY + 0.46, z);
      group.traverse(function (o) { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
      return group;
    }
    room.add(makeChair(1.5, -1.3, 0xd8b23a));
    room.add(makeChair(2.3, -2.2, 0x6fae5e));

    // small table
    var table = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.06, 0.7), new THREE.MeshStandardMaterial({ color: 0x6b3f22, roughness: 0.8 }));
    table.position.set(1.9, floorY + 0.55, -5.6);
    table.castShadow = true; table.receiveShadow = true;
    room.add(table);
    var tableLegGeo = new THREE.CylinderGeometry(0.035, 0.035, 0.5, 6);
    [[-0.28, -0.28], [0.28, -0.28], [-0.28, 0.28], [0.28, 0.28]].forEach(function (p) {
      var leg = new THREE.Mesh(tableLegGeo, new THREE.MeshStandardMaterial({ color: 0x4a2f1c, roughness: 0.8 }));
      leg.position.set(table.position.x + p[0], floorY + 0.25, table.position.z + p[1]);
      leg.castShadow = true;
      room.add(leg);
    });

    // two small framed pictures on the back wall
    [[-2.6, 1.0, 0x2e2a22], [-2.6, 0.15, 0x3a2a20]].forEach(function (p) {
      var frame = new THREE.Mesh(new THREE.PlaneGeometry(0.55, 0.4), new THREE.MeshStandardMaterial({ color: p[2], roughness: 0.8 }));
      frame.position.set(p[0], p[1], -6.96);
      room.add(frame);
    });
  }

  // Scene 2 — an open landscape at sunset: sky dome, rolling hills
  // receding into haze, and a lone tree close to the window. No box here
  // — the sky dome itself guarantees there is always more world to see,
  // the open-air version of the enclosed room.
  function buildLandscapeScene(inst) {
    var scene = inst.scene;
    scene.fog = new THREE.Fog(0x8a6a52, 10, 36);
    scene.add(new THREE.HemisphereLight(0xffd7a8, 0x3a2f1a, 0.65));
    inst.addSun(0xffe6c2, -10, 2.2);

    var rim = new THREE.PointLight(0xff9a6a, 0.4, 30);
    rim.position.set(-4, 3, -6);
    scene.add(rim);

    buildSkyDome(scene, "#2a2350", "#e8875a", "#ffd9a0", 40);

    var groundY = -2.2;
    var ground = new THREE.Mesh(
      new THREE.PlaneGeometry(70, 70),
      new THREE.MeshStandardMaterial({ color: 0x4c7a3d, roughness: 1 })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.set(0, groundY, -15);
    ground.receiveShadow = true;
    scene.add(ground);

    // layered hills receding into the haze, like painted theater flats
    var hillColors = [0x3f6b34, 0x5c8a45, 0x86a15a, 0xb6a05a];
    [-6, -12, -20, -30].forEach(function (z, i) {
      var hill = new THREE.Mesh(
        new THREE.SphereGeometry(6 + i * 2, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2),
        new THREE.MeshStandardMaterial({ color: hillColors[i], roughness: 1 })
      );
      hill.scale.y = 0.35;
      hill.position.set((i % 2 === 0 ? -1 : 1) * 2, groundY, z);
      hill.receiveShadow = true;
      scene.add(hill);
    });

    // a lone tree close to the window
    var trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.12, 1.1, 8), new THREE.MeshStandardMaterial({ color: 0x4a2f1c, roughness: 0.9 }));
    trunk.position.set(-1.6, groundY + 0.55, 0.4);
    trunk.castShadow = true;
    scene.add(trunk);
    var foliage = new THREE.Mesh(new THREE.ConeGeometry(0.55, 1.3, 8), new THREE.MeshStandardMaterial({ color: 0x3f6b34, roughness: 0.9 }));
    foliage.position.set(trunk.position.x, trunk.position.y + 0.9, trunk.position.z);
    foliage.castShadow = true;
    scene.add(foliage);

    // a few smaller trees mid-ground
    [[-3, -4], [2.5, -3], [3.8, -7]].forEach(function (p) {
      var s = 0.5 + Math.random() * 0.3;
      var t = new THREE.Mesh(new THREE.CylinderGeometry(0.05 * s, 0.08 * s, 0.7 * s, 7), new THREE.MeshStandardMaterial({ color: 0x4a2f1c, roughness: 0.9 }));
      t.position.set(p[0], groundY + 0.35 * s, p[1]);
      t.castShadow = true;
      scene.add(t);
      var f = new THREE.Mesh(new THREE.ConeGeometry(0.4 * s, 1.0 * s, 7), new THREE.MeshStandardMaterial({ color: 0x527d3f, roughness: 0.9 }));
      f.position.set(p[0], t.position.y + 0.6 * s, p[1]);
      f.castShadow = true;
      scene.add(f);
    });

    var sunDisc = new THREE.Mesh(new THREE.CircleGeometry(1.2, 24), new THREE.MeshBasicMaterial({ color: 0xffe6b0, fog: false }));
    sunDisc.position.set(2, 2.6, -25);
    scene.add(sunDisc);
  }

  // Scene 3 — a city street at night: two rows of lit towers receding
  // toward a moon. Same open-air logic as the landscape (sky dome, no
  // box), but a completely different mood and depth rhythm — tall, dense,
  // vertical instead of low and rolling.
  function buildCityScene(inst) {
    var scene = inst.scene;
    scene.fog = new THREE.Fog(0x0a0e1a, 8, 34);
    scene.add(new THREE.HemisphereLight(0x3a4a7a, 0x05060c, 0.4));
    inst.addSun(0xbcd0ff, -14, 1.1);

    var rim = new THREE.PointLight(0xff9ad6, 0.45, 26);
    rim.position.set(-3, 2, -6);
    scene.add(rim);

    buildSkyDome(scene, "#05060f", "#141033", "#2c1f4a", 40);

    var moon = new THREE.Mesh(new THREE.SphereGeometry(0.9, 16, 16), new THREE.MeshBasicMaterial({ color: 0xeef2ff, fog: false }));
    moon.position.set(3.5, 4.5, -28);
    scene.add(moon);

    var groundY = -2.4;
    var street = new THREE.Mesh(
      new THREE.PlaneGeometry(14, 40),
      new THREE.MeshStandardMaterial({ map: makeStreetTexture(), roughness: 0.95 })
    );
    street.rotation.x = -Math.PI / 2;
    street.position.set(0, groundY, -14);
    street.receiveShadow = true;
    scene.add(street);

    function addBuildingRow(xSign) {
      var z = -3;
      for (var i = 0; i < 7; i++) {
        var w = 1.4 + Math.random() * 1.2;
        var h = 2 + Math.random() * 5.5;
        var depth = 1.4 + Math.random() * 1.2;
        var tex = makeWindowTexture("#12172a", "#ffd98a", 4, Math.max(4, Math.round(h * 2)));
        var b = new THREE.Mesh(
          new THREE.BoxGeometry(w, h, depth),
          new THREE.MeshStandardMaterial({ map: tex, roughness: 0.85 })
        );
        b.position.set(xSign * (3.2 + Math.random() * 1.2), groundY + h / 2, z);
        b.castShadow = true; b.receiveShadow = true;
        scene.add(b);
        z -= depth + 1.0 + Math.random() * 1.5;
      }
    }
    addBuildingRow(-1);
    addBuildingRow(1);
  }

  var SCENE_BUILDERS = {
    "van-gogh-room": buildBedroomScene,
    "landscape": buildLandscapeScene,
    "city-night": buildCityScene
  };

  function buildInstance(canvas, presetKey) {
    var inst = createBaseInstance(canvas);
    var build = SCENE_BUILDERS[presetKey] || buildBedroomScene;
    build(inst);
    return inst;
  }

  function disposeInstance(instance) {
    instance.scene.traverse(function (obj) {
      if (obj.geometry) { obj.geometry.dispose(); }
      if (obj.material) {
        var materials = Array.isArray(obj.material) ? obj.material : [obj.material];
        materials.forEach(function (m) {
          if (m.map) { m.map.dispose(); }
          m.dispose();
        });
      }
    });
    instance.renderer.dispose();
  }

  function setOffAxisProjection(cam, eye, halfW, halfH, near, far) {
    var pa = new THREE.Vector3(-halfW, -halfH, 0);
    var pb = new THREE.Vector3(halfW, -halfH, 0);
    var pc = new THREE.Vector3(-halfW, halfH, 0);

    var vr = new THREE.Vector3().subVectors(pb, pa).normalize();
    var vu = new THREE.Vector3().subVectors(pc, pa).normalize();
    var vn = new THREE.Vector3().crossVectors(vr, vu).normalize();

    var va = new THREE.Vector3().subVectors(pa, eye);
    var vb = new THREE.Vector3().subVectors(pb, eye);
    var vc = new THREE.Vector3().subVectors(pc, eye);

    var d = -va.dot(vn);
    var l = (vr.dot(va) * near) / d;
    var r = (vr.dot(vb) * near) / d;
    var b = (vu.dot(va) * near) / d;
    var t = (vu.dot(vc) * near) / d;

    cam.projectionMatrix.makePerspective(l, r, t, b, near, far);
    cam.projectionMatrixInverse.copy(cam.projectionMatrix).invert();

    var rotMat = new THREE.Matrix4().makeBasis(vr, vu, vn);
    cam.quaternion.setFromRotationMatrix(rotMat);
    cam.position.copy(eye);
    cam.updateMatrixWorld(true);
  }

  function getFullscreenElement() {
    return document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement || null;
  }

  // Must be called synchronously from the click handler — once an await
  // or promise resolution happens in between, the browser no longer
  // considers the request part of the user gesture and silently ignores
  // it. Failures (denied permission, unsupported browser) are swallowed
  // on purpose: the experience still opens, just not fullscreen.
  function requestFullscreen(el) {
    try {
      var fn = el.requestFullscreen || el.webkitRequestFullscreen || el.msRequestFullscreen;
      if (!fn) { return; }
      var result = fn.call(el);
      if (result && result.catch) { result.catch(function () {}); }
    } catch (e) { /* ignore */ }
  }

  function exitFullscreen() {
    try {
      var fn = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen;
      if (fn && getFullscreenElement()) {
        var result = fn.call(document);
        if (result && result.catch) { result.catch(function () {}); }
      }
    } catch (e) { /* ignore */ }
  }

  function setStatus(widget, text, tone) {
    if (!widget.status) { return; }
    widget.status.textContent = text;
    widget.status.dataset.tone = tone || "";
  }

  function resetWidgetUI(widget) {
    widget.canvas.hidden = true;
    if (widget.poster) { widget.poster.hidden = false; }
    widget.root.classList.remove("is-active");
    widget.openButton.hidden = false;
    widget.openButton.disabled = false;
    widget.openButton.textContent = "Abrir experiência";
    widget.closeButton.hidden = true;
    setStatus(widget, "", "");
  }

  function closeWidget(widget) {
    if (widget.instance) {
      disposeInstance(widget.instance);
      widget.instance = null;
    }
    resetWidgetUI(widget);
    if (currentOpen === widget) {
      currentOpen = null;
      stopCamera();
      if (rafId) { cancelAnimationFrame(rafId); rafId = 0; }
    }
  }

  function openWidget(widget) {
    if (currentOpen === widget) { return; }
    if (currentOpen) { closeWidget(currentOpen); }

    widget.openButton.disabled = true;
    widget.openButton.textContent = "Abrindo…";
    setStatus(widget, "Carregando motor 3D e modelo de rastreamento…", "");

    loadEngine()
      .then(function () {
        setStatus(widget, "Solicitando acesso à câmera…", "");
        return ensureCamera();
      })
      .then(function () {
        widget.instance = buildInstance(widget.canvas, widget.scenePreset);
        widget.canvas.hidden = false;
        if (widget.poster) { widget.poster.hidden = true; }
        widget.root.classList.add("is-active");
        widget.openButton.hidden = true;
        widget.closeButton.hidden = false;
        currentOpen = widget;
        setStatus(widget, "Rastreamento ativo", "ok");
        if (!rafId) { rafId = requestAnimationFrame(tick); }
      })
      .catch(function (err) {
        var message = "Não foi possível abrir (" + (err && err.message ? err.message : "erro desconhecido") + ").";
        setStatus(widget, message, "warn");
        widget.openButton.disabled = false;
        widget.openButton.textContent = "Tentar novamente";
      });
  }

  function trackFace() {
    if (!video || video.currentTime === lastVideoTime) { return; }
    lastVideoTime = video.currentTime;

    var result = faceLandmarker.detectForVideo(video, performance.now());
    if (result.faceLandmarks && result.faceLandmarks.length > 0) {
      lastFaceSeenAt = performance.now();
      if (currentOpen) { setStatus(currentOpen, "Rastreamento ativo", "ok"); }

      var lm = result.faceLandmarks[0];
      var leftCorner = lm[LEFT_EYE_CORNER];
      var rightCorner = lm[RIGHT_EYE_CORNER];
      var leftIris = lm[LEFT_IRIS] || leftCorner;
      var rightIris = lm[RIGHT_IRIS] || rightCorner;

      var dx = (rightCorner.x - leftCorner.x) * video.videoWidth;
      var dy = (rightCorner.y - leftCorner.y) * video.videoHeight;
      var rawDist = Math.sqrt(dx * dx + dy * dy);
      smoothedEyePixelDist = smoothedEyePixelDist === null ? rawDist : smoothedEyePixelDist + (rawDist - smoothedEyePixelDist) * DIST_SMOOTHING;

      var ipdCm = 6.3;
      var distanceCm = (ASSUMED_FOCAL_PX * ipdCm) / Math.max(smoothedEyePixelDist, 1);

      var cx = (leftIris.x + rightIris.x) / 2;
      var cy = (leftIris.y + rightIris.y) / 2;
      var normX = (cx - 0.5) * 2;
      var normY = (cy - 0.5) * 2;

      var halfWidthAtDist = distanceCm * Math.tan((HFOV_DEG * Math.PI / 180) / 2);
      var halfHeightAtDist = halfWidthAtDist * (video.videoHeight / video.videoWidth);

      eyeCm.x = -normX * halfWidthAtDist;
      eyeCm.y = -normY * halfHeightAtDist;
      eyeCm.z = distanceCm;
    } else if (currentOpen && performance.now() - lastFaceSeenAt > FACE_LOST_TIMEOUT_MS) {
      setStatus(currentOpen, "Rosto não detectado", "warn");
    }
  }

  function tick() {
    if (!currentOpen || !currentOpen.instance) { rafId = 0; return; }
    rafId = requestAnimationFrame(tick);
    trackFace();

    smoothedEyeCm.x += (eyeCm.x - smoothedEyeCm.x) * POS_SMOOTHING;
    smoothedEyeCm.y += (eyeCm.y - smoothedEyeCm.y) * POS_SMOOTHING;
    smoothedEyeCm.z += (eyeCm.z - smoothedEyeCm.z) * POS_SMOOTHING;

    var UNIT = 10;
    var w = currentOpen;
    var rect = w.canvas.getBoundingClientRect();

    var cssW = Math.max(1, Math.round(rect.width));
    var cssH = Math.max(1, Math.round(rect.height));
    if (w.instance.lastW !== cssW || w.instance.lastH !== cssH) {
      w.instance.renderer.setSize(cssW, cssH, true);
      w.instance.lastW = cssW; w.instance.lastH = cssH;
    }

    var viewportCenterX = window.innerWidth / 2;
    var viewportCenterY = window.innerHeight / 2;
    var offsetXcm = (rect.left + rect.width / 2 - viewportCenterX) * CM_PER_CSS_PX;
    var offsetYcm = -(rect.top + rect.height / 2 - viewportCenterY) * CM_PER_CSS_PX;

    var eyeWorld = new THREE.Vector3(
      (smoothedEyeCm.x - offsetXcm) / UNIT,
      (smoothedEyeCm.y - offsetYcm) / UNIT,
      smoothedEyeCm.z / UNIT
    );

    var halfW = (cssW * CM_PER_CSS_PX / 2) / UNIT;
    var halfH = (cssH * CM_PER_CSS_PX / 2) / UNIT;

    w.instance.windowFrame.scale.set(halfW * 2, halfH * 2, 1);
    setOffAxisProjection(w.instance.camera, eyeWorld, halfW, halfH, 0.02, 50);

    w.instance.bodyProxy.position.x = eyeWorld.x * 0.85;
    w.instance.bodyProxy.position.y = eyeWorld.y * 0.85 - 0.3;
    w.instance.bodyProxy.position.z = clamp(eyeWorld.z * 0.3, 0.6, 2.2);
    w.instance.bodyProxy.scale.setScalar(clamp(6.5 / Math.max(smoothedEyeCm.z, 20), 0.7, 1.8));

    w.instance.floaters.forEach(function (f) {
      f.rotation.x += f.userData.spin * 0.01;
      f.rotation.y += f.userData.spin * 0.015;
    });

    w.instance.renderer.render(w.instance.scene, w.instance.camera);
  }

  function init() {
    var nodes = Array.prototype.slice.call(document.querySelectorAll("[data-depth-window]"));
    if (!nodes.length) { return; }

    nodes.forEach(function (root) {
      var canvas = root.querySelector(".depth-window-canvas");
      var poster = root.querySelector(".depth-window-poster");
      var openButton = root.querySelector(".depth-window-open");
      var closeButton = root.querySelector(".depth-window-close");
      var status = root.querySelector(".depth-window-status");
      if (!canvas || !openButton || !closeButton) { return; }

      var widget = {
        root: root, canvas: canvas, poster: poster,
        openButton: openButton, closeButton: closeButton, status: status,
        scenePreset: root.getAttribute("data-scene") || "van-gogh-room",
        instance: null
      };
      widgets.push(widget);

      openButton.addEventListener("click", function () {
        requestFullscreen(root); // must run synchronously in the click handler
        openWidget(widget);
      });
      closeButton.addEventListener("click", function () {
        exitFullscreen();
        closeWidget(widget);
      });
    });

    window.addEventListener("pagehide", function () {
      if (currentOpen) { closeWidget(currentOpen); }
    });

    // Pressing Escape (or any other browser UI for leaving fullscreen)
    // exits fullscreen on its own — this just makes sure that also tears
    // down the camera and the GPU context instead of leaving them running
    // behind a now-windowed page.
    function onFullscreenChange() {
      if (!getFullscreenElement() && currentOpen) { closeWidget(currentOpen); }
    }
    document.addEventListener("fullscreenchange", onFullscreenChange);
    document.addEventListener("webkitfullscreenchange", onFullscreenChange);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
