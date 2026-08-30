import { useEffect, useRef, useState } from "react";

const DELHI_CENTER = { lat: 28.6139, lng: 77.209 };
const SCRIPT_ID = "transit-sih-google-maps";
let googleMapsPromise;

function loadGoogleMaps(apiKey) {
  if (window.google?.maps) return Promise.resolve(window.google.maps);
  if (googleMapsPromise) return googleMapsPromise;

  googleMapsPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    script.async = true;
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&v=weekly&libraries=places`;
    script.onload = () => resolve(window.google.maps);
    script.onerror = () => reject(new Error("Google Maps could not be loaded."));
    document.head.appendChild(script);
  });

  return googleMapsPromise;
}

function placeLabel(place) {
  return place.formatted_address || place.name || "";
}

export default function GoogleMap({
  origin,
  destination,
  originInputRef,
  destinationInputRef,
  onOriginSelected,
  onDestinationSelected,
  isExpanded = false,
}) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const geocoderRef = useRef(null);
  const originMarkerRef = useRef(null);
  const destinationMarkerRef = useRef(null);
  const routePolylinesRef = useRef([]);
  const autocompleteBoundRef = useRef(false);
  const [mapError, setMapError] = useState("");
  const [mapReady, setMapReady] = useState(false);
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

  useEffect(() => {
    if (!apiKey) {
      setMapError("Google Maps key missing. Add VITE_GOOGLE_MAPS_API_KEY to .env.local.");
      return undefined;
    }

    let cancelled = false;
    loadGoogleMaps(apiKey)
      .then((maps) => {
        if (cancelled || !containerRef.current) return;

        mapRef.current = new maps.Map(containerRef.current, {
          center: DELHI_CENTER,
          zoom: 11,
          disableDefaultUI: true,
          zoomControl: true,
          gestureHandling: "greedy",
          styles: [
            { elementType: "geometry", stylers: [{ color: "#181b26" }] },
            { elementType: "labels.text.fill", stylers: [{ color: "#9aa3b8" }] },
            { elementType: "labels.text.stroke", stylers: [{ color: "#181b26" }] },
            { featureType: "road", elementType: "geometry", stylers: [{ color: "#2c3140" }] },
            { featureType: "water", elementType: "geometry", stylers: [{ color: "#173038" }] },
            { featureType: "poi", stylers: [{ visibility: "off" }] },
          ],
        });
        geocoderRef.current = new maps.Geocoder();
        setMapReady(true);

        if (!autocompleteBoundRef.current) {
          const bindAutocomplete = (input, onSelected) => {
            if (!input) return;
            const delhiBounds = new maps.LatLngBounds(
              new maps.LatLng(28.40, 76.90), // SW Delhi NCR
              new maps.LatLng(28.88, 77.45)  // NE Delhi NCR
            );
            const autocomplete = new maps.places.Autocomplete(input, {
              componentRestrictions: { country: "in" },
              bounds: delhiBounds,
              strictBounds: false,
              fields: ["formatted_address", "name", "geometry"],
              types: ["geocode", "establishment"],
            });
            autocomplete.addListener("place_changed", () => {
              const label = placeLabel(autocomplete.getPlace());
              if (label) onSelected(label);
            });
          };

          bindAutocomplete(originInputRef.current, onOriginSelected);
          bindAutocomplete(destinationInputRef.current, onDestinationSelected);
          autocompleteBoundRef.current = true;
        }
      })
      .catch((error) => {
        if (!cancelled) setMapError(error.message);
      });

    return () => {
      cancelled = true;
    };
  }, [apiKey, destinationInputRef, onDestinationSelected, onOriginSelected, originInputRef]);

  // Re-trigger map layout calculation when map expansion state changes
  useEffect(() => {
    if (mapReady && mapRef.current && window.google?.maps) {
      setTimeout(() => {
        window.google.maps.event.trigger(mapRef.current, "resize");
        if (!origin && !destination) {
          mapRef.current.setCenter(DELHI_CENTER);
        }
      }, 100);
    }
  }, [isExpanded, mapReady, origin, destination]);

  useEffect(() => {
    if (!mapReady || !mapRef.current || !geocoderRef.current || !window.google?.maps) return;

    let cancelled = false;
    const maps = window.google.maps;
    const bounds = new maps.LatLngBounds();
    let markerCount = 0;

    const showLocation = async (address, markerRef, title, color) => {
      if (!address.trim()) return;
      try {
        const { results } = await geocoderRef.current.geocode({ address: `${address}, Delhi, India` });
        if (cancelled || !results[0]) return;
        const position = results[0].geometry.location;
        markerRef.current?.setMap(null);
        markerRef.current = new maps.Marker({
          map: mapRef.current,
          position,
          title,
          icon: {
            path: maps.SymbolPath.CIRCLE,
            scale: 8,
            fillColor: color,
            fillOpacity: 1,
            strokeColor: "#10121A",
            strokeWeight: 2,
          },
        });
        bounds.extend(position);
        markerCount += 1;
      } catch {
        // Input can be incomplete while typing
      }
    };

    Promise.all([
      showLocation(origin, originMarkerRef, "Starting point", "#FFB020"),
      showLocation(destination, destinationMarkerRef, "Destination", "#9B8CFF"),
    ]).then(() => {
      if (!cancelled && markerCount) mapRef.current.fitBounds(bounds, markerCount === 1 ? 100 : 55);
    });

    return () => {
      cancelled = true;
    };
  }, [destination, mapReady, origin]);

  useEffect(() => {
    routePolylinesRef.current.forEach((polyline) => polyline.setMap(null));
    routePolylinesRef.current = [];

    if (!mapReady || !origin.trim() || !destination.trim() || !window.google?.maps) return undefined;

    let cancelled = false;

    const drawTransitRoute = async () => {
      try {
        const { Route } = await window.google.maps.importLibrary("routes");
        const { routes } = await Route.computeRoutes({
          origin: `${origin}, Delhi, India`,
          destination: `${destination}, Delhi, India`,
          travelMode: "TRANSIT",
          fields: ["path"],
        });

        if (cancelled || !routes?.[0]) return;

        routePolylinesRef.current = routes[0].createPolylines();
        routePolylinesRef.current.forEach((polyline) => polyline.setMap(mapRef.current));
      } catch {
        if (!cancelled) {
          setMapError("Could not draw a transit route. Check that the Routes API is enabled for this key.");
        }
      }
    };

    drawTransitRoute();

    return () => {
      cancelled = true;
    };
  }, [destination, mapReady, origin]);

  return (
    <div style={{ position: "absolute", inset: 0, background: "#181B26" }}>
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
      {!apiKey && (
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", pointerEvents: "none" }}>
          <svg viewBox="0 0 400 230" width="100%" height="100%" style={{ display: "block" }}>
            <rect width="400" height="230" fill="#181B26" />
            <path d="M0,190 C60,160 90,210 140,185 C190,160 210,205 260,190 L400,230 L0,230 Z" fill="#173038" opacity="0.55" />
            {[30, 90, 150, 210, 270, 330].map((x) => (
              <line key={"v" + x} x1={x} y1="0" x2={x - 30} y2="230" stroke="#2C3140" strokeWidth="1" opacity="0.5" />
            ))}
            {[20, 60, 100, 140, 180].map((y) => (
              <line key={"h" + y} x1="0" y1={y} x2="400" y2={y + 10} stroke="#2C3140" strokeWidth="1" opacity="0.4" />
            ))}
            <g transform="translate(200,100)">
              <circle r="12" fill="#FFB020" opacity="0.2" />
              <circle r="4" fill="#FFB020" />
            </g>
          </svg>
        </div>
      )}
      {mapError && (
        <div style={{ position: "absolute", left: 16, right: 16, bottom: 20, padding: "8px 12px", borderRadius: 10, background: "rgba(16,18,26,0.92)", border: "1px solid #FF6859", color: "#FFB0A8", fontSize: 11, lineHeight: 1.4, zIndex: 10 }}>
          {mapError}
        </div>
      )}
    </div>
  );
}
