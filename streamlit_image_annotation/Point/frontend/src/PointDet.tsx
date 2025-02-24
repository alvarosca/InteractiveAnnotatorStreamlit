import {
  Streamlit,
  withStreamlitConnection,
  ComponentProps
} from "streamlit-component-lib"
import React, { useEffect, useState, useRef } from "react"
import { ChakraProvider, Box, HStack, Center } from '@chakra-ui/react'

import useImage from 'use-image';
import ThemeSwitcher from './ThemeSwitcher'
import PointCanvas from "./PointCanvas";

export interface PythonArgs {
  image_url: string,
  mask_url: string,
  contour_url: string,
  image_size: number[],
  label_list: string[],
  points_info: any[],
  color_map: any,
  point_width: number,
  use_space: boolean,
  mode: string,
  label: string,
  zoom: number,
  mask_trans: number,
  contour_trans: number
}

const PointDet = ({ args, theme }: ComponentProps) => {
  const {
    image_url,
    mask_url,
    contour_url,
    image_size,
    label_list,
    points_info,
    color_map,
    point_width,
    mode,
    label,
    zoom,
    mask_trans,
    contour_trans,
  }: PythonArgs = args

  const params = new URLSearchParams(window.location.search);
  const baseUrl = params.get('streamlitUrl')
  const [image] = useImage(baseUrl + image_url)
  const [mask] = useImage(baseUrl + mask_url)
  const [contour] = useImage(baseUrl + contour_url)
  const [pointsInfo, setPointsInfo] = useState(
    points_info.map((p, i) => ({
      x: p.point[0],
      y: p.point[1],
      label: p.label,
      stroke: color_map[p.label],
      id: 'point-' + i
    }))
  );

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [scale, setScale] = useState(1.0);
  const updateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const resizeCanvas = () => {
      const scale_ratio = window.innerWidth / image_size[0];
      setScale(Math.min(scale_ratio, 1.0));
      Streamlit.setFrameHeight(image_size[1] * Math.min(scale_ratio, 1.0));
    };
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();
    return () => window.removeEventListener('resize', resizeCanvas);
  }, [image_size]);

  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      if (!selectedId) return;

      const selectedPoint = pointsInfo.find(p => p.id === selectedId);
      if (!selectedPoint) return;

      const currentIndex = label_list.indexOf(selectedPoint.label);
      let newLabel = selectedPoint.label;

      // Delete Point (Backslash or Backspace)
      if (event.key === "\\" || event.code === "Backslash" || event.code === "IntlBackslash" || event.key === "Backspace") {
        setPointsInfo(prevPoints => prevPoints.filter(p => p.id !== selectedId));
        setSelectedId(null);
        return;
      }

      if (event.key === "Shift") {
        newLabel = label_list[(currentIndex + 1) % label_list.length]; // Next label
      }

      if (newLabel !== selectedPoint.label) {
        setPointsInfo(prevPoints =>
          prevPoints.map(p =>
            p.id === selectedId ? { ...p, label: newLabel, stroke: color_map[newLabel] } : p
          )
        );
      }
    };

    window.addEventListener("keydown", handleKeyPress);
    return () => {
      window.removeEventListener("keydown", handleKeyPress);
    };
  }, [selectedId, pointsInfo]);

  useEffect(() => {
    if (updateTimeoutRef.current) {
      clearTimeout(updateTimeoutRef.current);
    }

    updateTimeoutRef.current = setTimeout(() => {
      const currentPointsValue = pointsInfo.map(point => ({
        point: [point.x, point.y],
        label_id: label_list.indexOf(point.label),
        label: point.label
      }));
      Streamlit.setComponentValue(currentPointsValue);
    }, 1000); // Delay of 1 second
  }, [pointsInfo]);

  return (
    <ChakraProvider>
      <ThemeSwitcher theme={theme}>
        <Center>
          <HStack width="100%" height="100%">
            <Box 
              width="100%" 
              style={{
                overflow: 'auto',  
                maxWidth: '100%',  
                maxHeight: '100vh', 
                position: 'relative' 
              }}
            >
              <PointCanvas
                pointsInfo={pointsInfo}
                mode={mode} 
                selectedId={selectedId}
                scale={scale}
                setSelectedId={setSelectedId}
                setPointsInfo={setPointsInfo}
                setLabel={() => {}}
                color_map={color_map}
                label={label} 
                image={image}
                mask={mask}
                contour={contour}
                image_size={image_size}
                strokeWidth={point_width}
                zoom={zoom}
                maskOpacity={mask_trans}
                contourOpacity={contour_trans}
              />
            </Box>
          </HStack>
        </Center>
      </ThemeSwitcher>
    </ChakraProvider>
  )
}

export default withStreamlitConnection(PointDet);
