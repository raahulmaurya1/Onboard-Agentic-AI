// import React, { useRef, useEffect } from 'react';

// /**
//  * Globe3D
//  * An interactive 3D globe built with Three.js (loaded from CDN via dynamic import).
//  * Features: teal wireframe sphere, gold orbiting rings, glowing dots, floating particles.
//  * Mouse movement tilts the globe gently.
//  */
// export default function Globe3D() {
//   const mountRef = useRef(null);

//   useEffect(() => {
//     const mount = mountRef.current;
//     if (!mount) return;

//     let animFrameId;
//     let renderer;

//     // Dynamically import Three.js (installed via npm)
//     import('three').then((THREE) => {
//       const w = mount.clientWidth;
//       const h = mount.clientHeight;

//       // ---- Scene setup ----
//       const scene = new THREE.Scene();
//       const camera = new THREE.PerspectiveCamera(60, w / h, 0.1, 100);
//       camera.position.z = 2.8;

//       renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
//       renderer.setSize(w, h);
//       renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
//       renderer.setClearColor(0x000000, 0);
//       mount.appendChild(renderer.domElement);

//       // ---- Globe sphere ----
//       const sphereGeo = new THREE.SphereGeometry(1, 64, 64);

//       // Solid base (very transparent teal)
//       const solidMat = new THREE.MeshPhongMaterial({
//         color: 0x0d9488,
//         emissive: 0x0d4a45,
//         transparent: true,
//         opacity: 0.12,
//       });
//       scene.add(new THREE.Mesh(sphereGeo, solidMat));

//       // Wireframe overlay
//       const wireMat = new THREE.MeshBasicMaterial({
//         color: 0x5eead4,
//         wireframe: true,
//         transparent: true,
//         opacity: 0.32,
//       });
//       const wireframe = new THREE.Mesh(sphereGeo, wireMat);
//       scene.add(wireframe);

//       // ---- Dots on sphere surface (Fibonacci spiral) ----
//       const positions = [];
//       const colors = [];
//       for (let i = 0; i < 300; i++) {
//         const phi = Math.acos(-1 + (2 * i) / 300);
//         const theta = Math.sqrt(300 * Math.PI) * phi;
//         positions.push(
//           1.02 * Math.cos(theta) * Math.sin(phi),
//           1.02 * Math.sin(theta) * Math.sin(phi),
//           1.02 * Math.cos(phi)
//         );
//         const t = Math.random();
//         // Mix gold and teal dots
//         if (t > 0.65) {
//           colors.push(0.93, 0.68, 0.0); // gold
//         } else {
//           colors.push(0.37, 0.92, 0.83); // teal
//         }
//       }
//       const dotsGeo = new THREE.BufferGeometry();
//       dotsGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
//       dotsGeo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
//       const dotsMat = new THREE.PointsMaterial({
//         size: 0.022,
//         vertexColors: true,
//         transparent: true,
//         opacity: 0.85,
//       });
//       const dots = new THREE.Points(dotsGeo, dotsMat);
//       scene.add(dots);

//       // ---- Orbiting rings ----
//       const ringDefs = [
//         { size: 1.16, angle: 0,           color: 0xEDAD00, speed: 0.008 },
//         { size: 1.22, angle: Math.PI / 3, color: 0x5eead4, speed: -0.006 },
//         { size: 1.28, angle: -Math.PI / 3,color: 0xEDAD00, speed: 0.007 },
//         { size: 1.34, angle: Math.PI / 2, color: 0x5eead4, speed: -0.005 },
//       ];
//       const rings = ringDefs.map(({ size, angle, color, speed }) => {
//         const mesh = new THREE.Mesh(
//           new THREE.TorusGeometry(size, 0.006, 8, 120),
//           new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.55 })
//         );
//         mesh.rotation.x = angle;
//         mesh.rotation.y = angle * 0.5;
//         mesh.userData.speed = speed;
//         scene.add(mesh);
//         return mesh;
//       });

//       // ---- Floating particles around globe ----
//       const pPos = [];
//       for (let i = 0; i < 80; i++) {
//         const r = 1.4 + Math.random() * 0.6;
//         const theta = Math.random() * Math.PI * 2;
//         const phi = Math.random() * Math.PI;
//         pPos.push(
//           r * Math.sin(phi) * Math.cos(theta),
//           r * Math.sin(phi) * Math.sin(theta),
//           r * Math.cos(phi)
//         );
//       }
//       const particlesGeo = new THREE.BufferGeometry();
//       particlesGeo.setAttribute('position', new THREE.Float32BufferAttribute(pPos, 3));
//       const particles = new THREE.Points(
//         particlesGeo,
//         new THREE.PointsMaterial({ color: 0xEDAD00, size: 0.04, transparent: true, opacity: 0.65 })
//       );
//       scene.add(particles);

//       // ---- Lighting ----
//       scene.add(new THREE.AmbientLight(0xffffff, 0.5));
//       const pl1 = new THREE.PointLight(0x5eead4, 2, 10);
//       pl1.position.set(3, 3, 3);
//       scene.add(pl1);
//       const pl2 = new THREE.PointLight(0xEDAD00, 1.5, 10);
//       pl2.position.set(-3, -2, 2);
//       scene.add(pl2);

//       // ---- Mouse interaction ----
//       let mouseX = 0;
//       let mouseY = 0;
//       const onMouseMove = (e) => {
//         const rect = mount.getBoundingClientRect();
//         mouseX = ((e.clientX - rect.left) / w - 0.5) * 2;
//         mouseY = -((e.clientY - rect.top) / h - 0.5) * 2;
//       };
//       mount.addEventListener('mousemove', onMouseMove);

//       // ---- Animation loop ----
//       let t = 0;
//       const animate = () => {
//         animFrameId = requestAnimationFrame(animate);
//         t += 0.005;

//         wireframe.rotation.y += 0.003;
//         dots.rotation.y += 0.003;
//         particles.rotation.y -= 0.002;

//         rings.forEach((ring) => {
//           ring.rotation.z += ring.userData.speed;
//         });

//         // Gentle tilt toward mouse
//         wireframe.rotation.x += (mouseY * 0.05 - wireframe.rotation.x) * 0.05;
//         dots.rotation.x = wireframe.rotation.x;

//         // Pulsing opacity
//         wireMat.opacity = 0.22 + 0.12 * Math.sin(t * 2);
//         dotsMat.opacity = 0.65 + 0.2 * Math.sin(t * 1.5);

//         renderer.render(scene, camera);
//       };
//       animate();

//       // ---- Resize handler ----
//       const handleResize = () => {
//         if (!mount) return;
//         const nw = mount.clientWidth;
//         const nh = mount.clientHeight;
//         camera.aspect = nw / nh;
//         camera.updateProjectionMatrix();
//         renderer.setSize(nw, nh);
//       };
//       window.addEventListener('resize', handleResize);

//       // Cleanup stored for unmount
//       mount._cleanup = () => {
//         window.removeEventListener('resize', handleResize);
//         mount.removeEventListener('mousemove', onMouseMove);
//         cancelAnimationFrame(animFrameId);
//         renderer.dispose();
//         if (mount.contains(renderer.domElement)) {
//           mount.removeChild(renderer.domElement);
//         }
//       };
//     });

//     return () => {
//       if (mount._cleanup) mount._cleanup();
//       cancelAnimationFrame(animFrameId);
//     };
//   }, []);

//   return (
//     <div
//       ref={mountRef}
//       style={{
//         width: '100%',
//         height: '520px',
//         cursor: 'grab',
//         borderRadius: '12px',
//         overflow: 'hidden',
//       }}
//     />
//   );
// }



import React, { useRef, useEffect } from 'react';

/**
 * Globe3D
 * Exact port of the working HTML version globe, plus smooth mouse tilt.
 *
 * Elements (same as HTML):
 *  - Teal MeshPhong sphere base
 *  - Teal wireframe overlay (opacity pulses)
 *  - 300 Fibonacci-spiral surface dots (gold/teal mix, opacity pulses)
 *  - 4 orbiting gold/teal rings at different angles
 *  - 80 gold ambient particles drifting around
 *  - 2 point lights (teal + gold)
 *
 * Mouse: gentle tilt toward cursor (same lerp as HTML, just smoothed a touch more)
 */
export default function Globe3D() {
  const mountRef = useRef(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    let animFrameId;
    let cleanupFn;

    import('three').then((THREE) => {
      if (!mountRef.current) return;

      const w = mount.clientWidth;
      const h = mount.clientHeight;

      /* ── Renderer ── */
      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      renderer.setSize(w, h);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.setClearColor(0x000000, 0);
      mount.appendChild(renderer.domElement);

      /* ── Scene / Camera ── */
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(60, w / h, 0.1, 100);
      camera.position.z = 2.8;

      /* ── Sphere base ── */
      const sphereGeo = new THREE.SphereGeometry(1, 64, 64);

      scene.add(
        new THREE.Mesh(
          sphereGeo,
          new THREE.MeshPhongMaterial({
            color: 0x0d9488,
            emissive: 0x0d4a45,
            transparent: true,
            opacity: 0.15,
          })
        )
      );

      /* ── Wireframe ── */
      const wireMat = new THREE.MeshBasicMaterial({
        color: 0x5eead4,
        wireframe: true,
        transparent: true,
        opacity: 0.35,
      });
      const wireframe = new THREE.Mesh(sphereGeo, wireMat);
      scene.add(wireframe);

      /* ── Surface dots (Fibonacci spiral, 300 pts) ── */
      const pos = [];
      const col = [];
      for (let i = 0; i < 300; i++) {
        const phi   = Math.acos(-1 + (2 * i) / 300);
        const theta = Math.sqrt(300 * Math.PI) * phi;
        pos.push(
          1.01 * Math.cos(theta) * Math.sin(phi),
          1.01 * Math.sin(theta) * Math.sin(phi),
          1.01 * Math.cos(phi)
        );
        const t = Math.random();
        // t > 0.7 → gold-ish  |  else → teal-ish  (matches HTML exactly)
        col.push(t > 0.7 ? 0.95 : 0.4, t > 0.7 ? 0.85 : 0.95, t > 0.7 ? 0.3 : 0.85);
      }
      const dotsGeo = new THREE.BufferGeometry();
      dotsGeo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
      dotsGeo.setAttribute('color',    new THREE.Float32BufferAttribute(col, 3));
      const dotsMat = new THREE.PointsMaterial({
        size: 0.022,
        vertexColors: true,
        transparent: true,
        opacity: 0.9,
      });
      const dots = new THREE.Points(dotsGeo, dotsMat);
      scene.add(dots);

      /* ── 4 Orbiting rings ── */
      const ringDefs = [
        [0,            0xEDAD00],
        [Math.PI / 3,  0x5eead4],
        [-Math.PI / 3, 0xEDAD00],
        [Math.PI / 2,  0x5eead4],
      ];
      const rings = ringDefs.map(([a, c]) => {
        const m = new THREE.Mesh(
          new THREE.TorusGeometry(1.15, 0.006, 8, 120),
          new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0.6 })
        );
        m.rotation.x = a;
        m.rotation.y = a * 0.5;
        scene.add(m);
        return m;
      });
      // Spread radii slightly so rings don't overlap (matching HTML 1.15+i*0.06)
      rings.forEach((r, i) => { r.scale.setScalar(1 + i * 0.06); });

      /* ── 80 ambient gold particles ── */
      const ppos = [];
      for (let i = 0; i < 80; i++) {
        const r = 1.4 + Math.random() * 0.5;
        const t = Math.random() * Math.PI * 2;
        const p = Math.random() * Math.PI;
        ppos.push(
          r * Math.sin(p) * Math.cos(t),
          r * Math.sin(p) * Math.sin(t),
          r * Math.cos(p)
        );
      }
      const particlesGeo = new THREE.BufferGeometry();
      particlesGeo.setAttribute('position', new THREE.Float32BufferAttribute(ppos, 3));
      const particles = new THREE.Points(
        particlesGeo,
        new THREE.PointsMaterial({ color: 0xEDAD00, size: 0.04, transparent: true, opacity: 0.7 })
      );
      scene.add(particles);

      /* ── Lighting ── */
      scene.add(new THREE.AmbientLight(0xffffff, 0.5));
      const pl1 = new THREE.PointLight(0x5eead4, 2, 10);
      pl1.position.set(3, 3, 3);
      scene.add(pl1);
      const pl2 = new THREE.PointLight(0xEDAD00, 1.5, 10);
      pl2.position.set(-3, -2, 2);
      scene.add(pl2);

      /* ── Mouse tracking ── */
      let mx = 0;
      let my = 0;
      const onMouseMove = (e) => {
        const rect = mount.getBoundingClientRect();
        mx =  ((e.clientX - rect.left) / rect.width  - 0.5) * 1;
        my = -((e.clientY - rect.top)  / rect.height - 0.5) * 2;
      };
      mount.addEventListener('mousemove', onMouseMove);

      /* ── Animation loop (exact HTML logic) ── */
      let t = 0;
      const animate = () => {
        animFrameId = requestAnimationFrame(animate);
        t += 0.005;

        // Spin
        wireframe.rotation.y += 0.003;
        dots.rotation.y      += 0.003;
        particles.rotation.y -= 0.002;

        // Ring rotations (same axes/speeds as HTML)
        rings[0].rotation.z += 0.008;
        rings[1].rotation.z -= 0.006;
        rings[2].rotation.x += 0.007;
        rings[3].rotation.y += 0.005;

        // Mouse tilt (lerp toward mx/my, same 0.05 factor as HTML)
        wireframe.rotation.x += (my * 0.05 - wireframe.rotation.x) * 0.05;
        dots.rotation.x       = wireframe.rotation.x;
        particles.rotation.x  = wireframe.rotation.x * 0.4;

        // Pulsing opacity (same as HTML)
        wireMat.opacity  = 0.25 + 0.1  * Math.sin(t * 2);
        dotsMat.opacity  = 0.7  + 0.2  * Math.sin(t * 1.5);

        renderer.render(scene, camera);
      };
      animate();

      /* ── Resize ── */
      const handleResize = () => {
        if (!mount) return;
        const nw = mount.clientWidth;
        const nh = mount.clientHeight;
        camera.aspect = nw / nh;
        camera.updateProjectionMatrix();
        renderer.setSize(nw, nh);
      };
      window.addEventListener('resize', handleResize);

      cleanupFn = () => {
        window.removeEventListener('resize', handleResize);
        mount.removeEventListener('mousemove', onMouseMove);
        cancelAnimationFrame(animFrameId);
        renderer.dispose();
        if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement);
      };
    });

    return () => {
      cancelAnimationFrame(animFrameId);
      if (cleanupFn) cleanupFn();
    };
  }, []);

  return (
    <div
      ref={mountRef}
      style={{
        width: '100%',
        height: '520px',
        cursor: 'grab',
        borderRadius: '12px',
        overflow: 'hidden',
      }}
    />
  );
}