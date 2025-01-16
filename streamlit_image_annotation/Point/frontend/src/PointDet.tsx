import {
  Streamlit,
  withStreamlitConnection,
  ComponentProps
} from "streamlit-component-lib"
import React, { useEffect, useState } from "react"
import { ChakraProvider, Box, Spacer, HStack, Center } from '@chakra-ui/react'

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
  mode: string,   // <-- Added "mode" to the Python arguments
  label: string,  // <-- Added "label" to the Python arguments
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
    use_space,
    mode,  // <-- Extract "mode" from the args
    label,  // <-- Extract "label" from the args
    zoom,
    mask_trans,
    contour_trans,
  }: PythonArgs = args

  const params = new URLSearchParams(window.location.search);
  const baseUrl = params.get('streamlitUrl')
  const [image] = useImage(baseUrl + image_url)
  const [mask] = useImage(baseUrl + mask_url)
  const [contour] = useImage(baseUrl + contour_url)
  const [pointsInfo, setPointsInfo] = React.useState(
    points_info.map((p, i) => {
      return {
        x: p.point[0],
        y: p.point[1],
        label: p.label,
        stroke: color_map[p.label],
        id: 'point-' + i
      }
    })
  );

  const [selectedId, setSelectedId] = React.useState<string | null>(null);

  const [scale, setScale] = useState(1.0)
  useEffect(() => {
    const resizeCanvas = () => {
      const scale_ratio = window.innerWidth / image_size[0]
      setScale(Math.min(scale_ratio, 1.0))
      Streamlit.setFrameHeight(image_size[1] * Math.min(scale_ratio, 1.0))
    }
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas()
  }, [image_size])

  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      if (use_space && event.key === ' ') { 
        const currentPointsValue = pointsInfo.map((point, i) => {
          return {
            point: [point.x, point.y],
            label_id: label_list.indexOf(point.label),
            label: point.label
          }
        })
        Streamlit.setComponentValue(currentPointsValue)
      }
    };
    window.addEventListener('keydown', handleKeyPress);
    return () => {
      window.removeEventListener('keydown', handleKeyPress);
    };
  }, [pointsInfo]); 

  // This effect runs only when pointsInfo changes
  useEffect(() => {
    // Only set the component value when pointsInfo changes
    const currentPointsValue = pointsInfo.map((point, i) => {
      return {
        point: [point.x, point.y],
        label_id: label_list.indexOf(point.label),
        label: point.label
      }
    })
    Streamlit.setComponentValue(currentPointsValue)
  }, [pointsInfo]); // Triggered when pointsInfo changes

  return (
    <ChakraProvider>
      <ThemeSwitcher theme={theme}>
        <Center>
          <HStack width="100%" height="100%">
            <Box 
              width="100%" 
              style={{
                overflow: 'auto',  // Scrollbars enabled if content overflows
                maxWidth: '100%',  // Restrict width to avoid unnecessary scroll
                maxHeight: '100vh', // Set the max height relative to the viewport
                position: 'relative' // Needed for proper overflow control
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

export default withStreamlitConnection(PointDet)