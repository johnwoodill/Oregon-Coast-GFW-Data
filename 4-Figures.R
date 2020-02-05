library(tidyverse)
library(ggthemes)
library(feather)
library(viridis)
library(lubridate)
library(stringr)
library(marmap)
library(cowplot)
library(ggmap)
library(rgdal)

# Oregon Data
dat <- read_csv('~/Projects/Oregon-Coast-GFW-Data/data/OregonCoast_GFW_2016-2018.csv')

# Remove duplicates
dat <- dat[duplicated(dat$message_id), ]

# Filter Oregon
dat <- filter(dat, lat <= 46.23)

shape <- readOGR("~/Projects/Oregon-Coast-GFW-Data/data/Oregon Coast Shapefile/oregon_coastline.shp", layer = "oregon_coastline")
coords <- coordinates(shape)
coords2 <- unlist(coords)

y <- coords2[coords2 >= 0]
x <- coords2[coords2 < 0]

xycoords <- data.frame(y = y, x = x)
xycoords <- filter(xycoords, x <= -123.85)
ggplot(xycoords, aes(x, y)) + geom_point()

check <- function(ndat){
  # print(nrow(ndat))
  x1 = ndat[2]
  y1 = ndat[1]
  # print(x1)
  # print(y1)
  check_dat = data.frame()
  ncoords <- filter(xycoords, y <= y1 + 0.1 & y >= y1 - 0.1)
  if (nrow(ncoords) != 0){
    for (i in 1:nrow(ncoords)){
      # print(i)
      ccheck <- ifelse(x1 <= ncoords$x[i], 1, 0)
      check_dat <- rbind(check_dat, ccheck)
    }
    sumcheck <- sum(check_dat)
    if (sumcheck == nrow(ncoords)){
        return("OCEAN")
      } else {
        return("LAND")
      }}
  else {
    return("NA")
  }
  
}

x1 = dat$lon[1]
y1 = dat$lat[1]
y1
x1

check(dat[200, 7:8])

dat2 <- dat[1:100, ]

dat$loc <- apply(dat[,7:8], 1, FUN=check)

write_csv(dat, "~/Projects/Oregon-Coast-GFW-Data/data/COMPLETE_OregonCoast_GFW_2016-2018.csv")


ggplot(dat2, aes(lon, lat)) + geom_point(color="red") + geom_point(data=xycoords, aes(x, y))

# Custom color palette
cbp1 <- c("#999999", "#E69F00", "#56B4E9", "#009E73",
          "#0072B2", "#D55E00", "#CC79A7")

# Google key for map
gkey <- read_file("~/Projects/predicting-illegal-fishing/Google_api_key.txt")
register_google(key = gkey)

LON1 = -134
LON2 = -123
LAT1 = 42
LAT2 = 49

# EEZ line
#eez <- as.data.frame(read_csv("~/Projects/Puerto_Madryn_IUU_Fleet_Behavior/data/Argentina_EEZ.csv"))
#eez <- filter(eez, lon >= LON1 & lon <= LON2)
#eez <- filter(eez, lat >= LAT1 & lat <= LAT2)
#eez <- filter(eez, order <= 28242)

# dat$lat_lon <- paste0(dat$lat1, "_", dat$lon1)
# 
# dat2 <- dat %>% group_by(date, lat_lon) %>% 
#   summarise(fh = sum(fishing_hours))
# nrow(dat)


# ------------------------------------------------------------------------------------
# Figure 1. Map of Region


# Correct 4/24/2019
bat <- getNOAA.bathy(LON1-10, LON2+10, LAT1-10, LAT2+10, res = 1, keep = TRUE)

map2 <- 
  autoplot(bat, geom = c("raster", "contour")) +
  geom_raster(aes(fill=z)) +
  geom_contour(aes(z = z), colour = "white", alpha = 0.05) +
  scale_fill_gradientn(values = scales::rescale(c(-6600, 30, 40, 1500)),
                       colors = c("lightsteelblue4", "lightsteelblue2", "#C6E0FC",
                                  "grey50", "grey70", "grey85")) +
  geom_point(data = dat2, aes(lon, lat), alpha = 0.25) +
  theme(axis.title.x=element_blank(),
        axis.text.x=element_blank(),
        axis.ticks.x=element_blank(),
        axis.title.y=element_blank(),
        axis.text.y=element_blank(),
        axis.ticks.y=element_blank(),
        legend.direction = 'horizontal',
        legend.justification = 'center',
        legend.position = "bottom",
        legend.key=element_blank(),
        # legend.position = c(.93, 0.2),
        # legend.margin=margin(l = 0, unit='cm'),
        #element_text(margin = margin(r = 10, unit = "pt"))
        legend.text = element_text(size=8.5, margin = margin(r = 5, unit = "pt")),
        # legend.text = element_text(size=8.5),
        legend.title = element_text(size=9),
        legend.background = element_blank(),
        # legend.spacing.x = unit(0.30, 'cm'),
        # legend.key.size = unit(0, 'lines'),
        # legend.key.size = unit(0, "cm"),
        legend.box.background = element_rect(colour = "black"),
        # legend.key = element_rect(fill = "transparent", colour = "transparent"),
        # legend.background = element_rect(fill = "transparent", colour = "transparent"),
        panel.grid = element_blank(),
        panel.border = element_rect(colour = "black", fill=NA, size=1)) +
  guides(fill = FALSE,
         color = guide_legend(title.position = "bottom",
                              title.hjust = 0.5,
                              override.aes=list(fill=NA, shape=15, size=4),
                              keywidth=0.01,
                              keyheight=0.01,
                              default.unit="inch")) +
  
  # hjust = 0.5 centres the title horizontally
  # title.hjust = 0.5,
  #label.position = "top")
  
  scale_color_manual(values = c("cornflowerblue", "blue", "#C6E0FC", "#C6E0FC")) +
  # scale_color_gradientn(colours=brewer.pal(9, "OrRd"), limits=c(0, 200)) +
  # scale_y_continuous(expand=c(0,0)) +
  # scale_x_continuous(expand=c(0,0)) +
  NULL

map2
ggsave("~/Projects/Oregon-Coast-GFW-Data/figures/Figure1.png", width=5, height=5)
